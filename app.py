from flask import Flask, request, send_file, jsonify
import os
import io  # <-- Necessary import
import logging  # <-- Necessary import
from werkzeug.utils import secure_filename
from generate_reports import ReportGenerator # <-- Imports the class from the other file
import pandas as pd
import tempfile
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor

app = Flask(__name__)

logger = logging.getLogger(__name__)

DB_CONFIG = {
    'dbname': 'my_investors_db',
    'user': 'postgres',
    'password': 'your_new_strong_password',
    'host': 'localhost',
    'port': '5432'
}

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# --- THIS IS THE ROUTE YOUR N8N NODE IS CALLING ---
@app.route('/generate-report-by-id', methods=['POST'])
def generate_report_by_id():
    conn = None
    cur = None
    try:
        data = request.get_json()
        if not data or 'id' not in data:
            return jsonify({'error': 'No investor ID provided'}), 400

        investor_id = data['id']

        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=DictCursor)

        # Fetches all data for the report
        cur.execute("""
            SELECT id, investor_name, total_committed, total_drawdown_called,
            total_drawdown_received, total_undrawn, gross_irr,
            net_irr, nav, capital_returned, balance_capital,
            total_returned, email 
            FROM investors
            WHERE id = %s
        """, (investor_id,))
        
        result = cur.fetchone()
        
        if not result:
            return jsonify({'error': 'Investor not found'}), 404

        investor_data = dict(result)

        # Creates the generator and calls the function
        generator = ReportGenerator()
        
        # --- CORRECTLY UNPACKS THE 3 RETURN VALUES ---
        report_id, html_content, pdf_bytes = generator.generate_report(investor_data, save_to_db=True)

        # --- SENDS BACK THE URLS FOR THE NEXT N8N NODE ---
        response = {
            'success': True,
            'message': f'Generated report for {investor_data["investor_name"]}',
            'investor_id': investor_id,
            'report_id': report_id,
            'pdf_url': f'http://127.0.0.1:8080/get-report-pdf/{investor_id}',
            'html_url': f'http://127.0.0.1:8080/get-report-html/{investor_id}'
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in /generate-report-by-id: {str(e)}") 
        return jsonify({'error': str(e)}), 500
    
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# --- THIS ROUTE LETS N8N DOWNLOAD THE PDF ---
@app.route('/get-report-pdf/<int:investor_id>', methods=['GET'])
def get_report_pdf(investor_id):
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("SELECT pdf_report, report_id FROM investors WHERE id = %s", (investor_id,))
        result = cur.fetchone()
        
        if not result or not result[0]:
            return jsonify({'error': 'PDF report not found'}), 404

        pdf_data, report_id = result
        
        return send_file(
            io.BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'investor_report_{report_id or investor_id}.pdf'
        )

    except Exception as e:
        logger.error(f"Error in /get-report-pdf: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# --- THIS ROUTE LETS YOU VIEW THE HTML IN A BROWSER ---
@app.route('/get-report-html/<int:investor_id>', methods=['GET'])
def get_report_html(investor_id):
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("SELECT html_report FROM investors WHERE id = %s", (investor_id,))
        result = cur.fetchone()
        
        if not result or not result[0]:
            return jsonify({'error': 'HTML report not found'}), 404

        return result[0], 200, {'Content-Type': 'text/html; charset=utf-8'}

    except Exception as e:
        logger.error(f"Error in /get-report-html: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# --- (Other routes like /generate-report from file upload are omitted for brevity) ---

if __name__ == '__main__':
    app.run(debug=True, port=8080, host='127.0.0.1')