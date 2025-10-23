import os
import sys
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import pandas as pd
import pdfkit
from dotenv import load_dotenv
import logging
import subprocess
from utils import format_indian_currency, format_percentage
from decimal import Decimal
import psycopg2
from psycopg2.extras import DictCursor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get the directory containing the script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables
load_dotenv()

# Use absolute paths with BASE_DIR
OUTPUT_DIR = os.path.join(BASE_DIR, os.getenv('OUTPUT_DIR', 'generated_reports'))
TEMPLATE_DIR = os.path.join(BASE_DIR, os.getenv('TEMPLATE_DIR', 'report_template'))
DATA_FILE = os.path.join(BASE_DIR, os.getenv('DATA_FILE', 'investor_data.csv'))

# Database Configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'my_investors_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'your_new_strong_password'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

def check_wkhtmltopdf():
    """Check if wkhtmltopdf is installed"""
    # The 'r' here is CRITICAL for Windows paths. Do not remove it.
    wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    try:
        if os.path.exists(wkhtmltopdf_path):
            subprocess.run([wkhtmltopdf_path, '-V'], capture_output=True, check=True)
            return wkhtmltopdf_path
        else:
            raise FileNotFoundError
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("wkhtmltopdf is not installed or not found in the expected location.")
        logger.info("Please ensure wkhtmltopdf is installed at: " + wkhtmltopdf_path)
        return False

class ReportGenerator:
    def __init__(self):
        self.wkhtmltopdf_path = check_wkhtmltopdf()
        self.pdf_enabled = bool(self.wkhtmltopdf_path)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self.env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        self.template = self.env.get_template('investor_report_template.html')

    def load_data(self, file_path):
        """Load investor data from CSV or Excel file"""
        try:
            if file_path.endswith('.csv'):
                return pd.read_csv(file_path)
            else:
                return pd.read_excel(file_path)
        except Exception as e:
            logger.error(f"Error loading data file: {str(e)}")
            raise

    def validate_data(self, data):
        """Validate required fields and their types in the data"""
        required_fields = {
            'investor_name': str,
            'total_committed': (int, float),
            'total_drawdown_called': (int, float),
            'total_drawdown_received': (int, float),
            'total_undrawn': (int, float),
            'gross_irr': (int, float),
            'net_irr': (int, float),
            'nav': (int, float),
            'capital_returned': (int, float),
            'balance_capital': (int, float),
            'total_returned': (int, float)
        }
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        for field, expected_type in required_fields.items():
            value = data.get(field)
            if value is not None and not isinstance(value, expected_type):
                try:
                    if expected_type == str:
                        data[field] = str(value)
                    else:
                        data[field] = float(value) 
                except (TypeError, ValueError):
                    raise ValueError(f"Field '{field}' must be a number, got {type(value).__name__}")
            elif value is None and field in required_fields:
                if expected_type != str:
                    data[field] = 0.0

    def validate_data_consistency(self, data):
        """Validate that the data is internally consistent"""
        if abs(data['total_undrawn'] + data['total_drawdown_called'] - data['total_committed']) > 0.01:
            raise ValueError("Inconsistent data: total_undrawn + total_drawdown_called != total_committed")
        if abs(data['total_drawdown_called'] - data['total_drawdown_received']) > 0.01:
            logger.warning(f"Warning: Mismatch in drawdown amounts for {data['investor_name']}")
        if abs(data['balance_capital'] + data['capital_returned'] - data['nav']) > 0.01:
            logger.warning(f"Warning: NAV does not match balance_capital + capital_returned for {data['investor_name']}")

    def format_data(self, data):
        """Format currency and percentage values"""
        self.validate_data_consistency(data)
        
        currency_fields = [
            'total_committed', 'total_drawdown_called', 'total_drawdown_received',
            'total_undrawn', 'nav', 'capital_returned', 'balance_capital', 'total_returned'
        ]
        percentage_fields = ['gross_irr', 'net_irr']
        
        for field in currency_fields:
            if field in data and data[field] is not None:
                data[field] = format_indian_currency(data[field])
        for field in percentage_fields:
            if field in data and data[field] is not None:
                data[field] = format_percentage(data[field])
        
        return data

    # --- THIS IS THE FUNCTION THAT WAS MISSING ---
    def generate_report(self, investor_data, save_to_db=True):
        """Generate report for a single investor and save to database"""
        conn = None
        cur = None
        try:
            for key, value in investor_data.items():
                if isinstance(value, Decimal):
                    investor_data[key] = float(value)
            
            self.validate_data(investor_data)
            investor_data_formatted = self.format_data(investor_data.copy())
            investor_data_formatted['generated_date'] = datetime.now().strftime('%d %B %Y')
            investor_data_formatted['report_period'] = datetime.now().strftime('%B %Y')
            date_part = datetime.now().strftime('%y%m%d')
            
            conn = psycopg2.connect(**DB_CONFIG) if save_to_db else None
            cur = conn.cursor() if conn else None
            
            if save_to_db and cur:
                cur.execute("SELECT COUNT(*) FROM investors WHERE report_id LIKE %s", (f"INV{date_part}%",))
                sequence_number = cur.fetchone()[0] + 1
            else:
                existing_reports = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(f"investor_report_INV{date_part}")]
                sequence_number = len(existing_reports) + 1
            
            investor_data_formatted['report_id'] = f"INV{date_part}{sequence_number:02d}"
            
            html_content = self.template.render(investor_data_formatted)
            
            pdf_bytes = None
            if self.pdf_enabled:
                options = {
                    'page-size': 'A4', 'margin-top': '15mm', 'margin-right': '15mm',
                    'margin-bottom': '15mm', 'margin-left': '15mm', 'encoding': 'UTF-8',
                    'footer-right': '[page] of [topage]', 'enable-local-file-access': True
                }
                config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path)
                pdf_bytes = pdfkit.from_string(html_content, False, options=options, configuration=config)
            
            if save_to_db and cur and 'id' in investor_data:
                cur.execute("""
                    UPDATE investors 
                    SET pdf_report = %s, html_report = %s,
                        report_generated_at = %s, report_id = %s
                    WHERE id = %s
                """, (
                    psycopg2.Binary(pdf_bytes) if pdf_bytes else None,
                    html_content, datetime.now(),
                    investor_data_formatted['report_id'], investor_data['id']
                ))
                conn.commit()
                logger.info(f"Saved report to database for {investor_data.get('investor_name', 'Unknown')}")
            
            logger.info(f"Generated report for {investor_data.get('investor_name', 'Unknown')}")
            # This returns the 3 values your app.py file needs
            return investor_data_formatted['report_id'], html_content, pdf_bytes
            
        except Exception as e:
            logger.error(f"Error generating report for {investor_data.get('investor_name', 'Unknown')}: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
# --------------------------------------------------

# (The main() function for standalone testing remains the same)
def main():
    try:
        generator = ReportGenerator()
        data_df = generator.load_data(DATA_FILE)
        # ... (rest of main function) ...
    except Exception as e:
        logger.error(f"Critical error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()