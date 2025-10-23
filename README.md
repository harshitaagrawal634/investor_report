# Investor Report Automation Project

This project automatically generates custom PDF reports for investors, saves them to a database, and emails the reports as attachments. The entire process is orchestrated by an n8n workflow that calls a custom Python Flask API.

## How It Works

1.  **Trigger:** An **n8n workflow** starts (either on a schedule or manually).
2.  **Fetch Data:** n8n queries a **PostgreSQL database** to get the list of investors.
3.  **Loop:** The workflow loops through each investor, one by one.
4.  **Call API:** For each investor, n8n sends a POST request to a **Python Flask API** with the investor's ID.
5.  **Generate Report:** The Flask API fetches the investor's full details, generates a custom HTML report using a Jinja2 template, and converts it to a **PDF file** in memory.
6.  **Save to DB:** The API saves the generated PDF and HTML directly into the database as binary data (`BYTEA`) and text, along with a new `report_id`.
7.  **Download:** The n8n workflow receives the public URL for the newly saved PDF, downloads it, and prepares the email.
8.  **Send Email:** n8n merges the investor's data (like `email` and `investor_name`) with the PDF file and sends a personalized email with the report attached.

## Tech Stack

* **Automation:** n8n (Desktop or Cloud)
* **Backend API:** Python 3.10+ with Flask
* **Database:** PostgreSQL
* **Database Shell:** `psql` (command-line tool)
* **PDF Generation:** `pdfkit` (which requires `wkhtmltopdf`)

---

## Local Setup Instructions

To run this project on your local machine, you must set up all three components.

### 1. Prerequisites

Before you begin, you must install:
* [PostgreSQL](httpss://www.postgresql.org/download/)
* [Python 3.10+](httpss://www.python.org/downloads/)
* [Git](httpss://git-scm.com/downloads/)
* [n8n Desktop App](httpss://n8n.io/desktop/)
* [wkhtmltopdf](httpss://wkhtmltopdf.org/downloads.html) (This is **required** by the `pdfkit` library. Make sure to add it to your system's PATH).

### 2. Database (PostgreSQL) Setup

1.  After installing PostgreSQL, open the `psql` shell.
2.  Create the database:
    ```sql
    CREATE DATABASE my_investors_db;
    ```
3.  Connect to your new database:
    ```sql
    \c my_investors_db
    ```
4.  Create the `investors` table. This is the complete schema:
    ```sql
    CREATE TABLE investors (
        id SERIAL PRIMARY KEY,
        investor_name VARCHAR(255),
        email VARCHAR(255) UNIQUE NOT NULL,
        total_committed DECIMAL(15, 2),
        total_drawdown_called DECIMAL(15, 2),
        total_drawdown_received DECIMAL(15, 2),
        total_undrawn DECIMAL(15, 2),
        gross_irr DECIMAL(5, 2),
        net_irr DECIMAL(5, 2),
        nav DECIMAL(15, 2),
        capital_returned DECIMAL(15, 2),
        balance_capital DECIMAL(15, 2),
        total_returned DECIMAL(15, 2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        investment_date DATE,
        
        -- Columns for generated reports
        pdf_report BYTEA,
        html_report TEXT,
        report_id VARCHAR(255),
        report_generated_at TIMESTAMP
    );
    ```
5.  Insert some test data. Make sure to use your own email to receive the test:
    ```sql
    INSERT INTO investors 
    (investor_name, email, total_committed, total_drawdown_called, total_drawdown_received, total_undrawn, gross_irr, net_irr, nav, capital_returned, balance_capital, total_returned, investment_date)
    VALUES 
    ('Sonia Verma', 'your-email@gmail.com', 5000000.00, 2000000.00, 2000000.00, 3000000.00, 12.40, 10.90, 2135000.00, 500000.00, 1500000.00, 750000.00, '2024-01-15');
    
    INSERT INTO investors
    (investor_name, email, total_committed, total_drawdown_called, total_drawdown_received, total_undrawn, gross_irr, net_irr, nav, capital_returned, balance_capital, total_returned, investment_date)
    VALUES
    ('Neha Gupta', 'your-other-email@gmail.com', 5500000.00, 2300000.00, 2300000.00, 3200000.00, 13.40, 11.70, 2680000.00, 580000.00, 1720000.00, 890000.00, '2024-03-10');
    ```

### 3. API (Python) Setup

1.  Clone this repository to your machine:
    ```bash
    git clone [https://github.com/harshitaagrawal634/investor_report.git](https://github.com/harshitaagrawal634/investor_report.git)
    cd investor_report
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On Mac/Linux
    # source venv/bin/activate
    ```
3.  Install all required Python libraries:
    ```bash
    pip install -r requirements.txt
    ```
4.  Create your local environment file. **This file is private and NOT on GitHub.**
    * Create a new file in the folder named `.env`
    * Add your local database credentials to it. (This must match your local PostgreSQL password).
    ```ini
    DB_NAME="my_investors_db"
    DB_USER="postgres"
    DB_PASSWORD="your-postgres-password"
    DB_HOST="localhost"
    DB_PORT="5432"
    ```
5.  Run the API server!
    ```bash
    python app.py
    ```
    You should see it running on `http://127.0.0.1:8080/`. Keep this terminal open.

### 4. Automation (n8n) Setup

1.  Open your **n8n Desktop app**.
2.  Click **File > Import > From File...** (or find the **Download** / **Import from File...** option in your menu).
3.  Select the `My workflow.json` file you cloned from this repository.
4.  The workflow will appear on your canvas.
5.  **Configure Credentials:**
    * **PostgreSQL:** Double-click the `Execute a SQL query` node, select your credentials, or create new ones using the *same credentials* from your `.env` file (`localhost`, `postgres`, your password, etc.).
    * **Email:** Double-click the `Send email` node and select or create your SMTP credentials (e.g., your Gmail App Password).

---

## Running the Project

1.  Make sure your **PostgreSQL** database is running.
2.  Make sure your **Python API** is running (with `python app.py`).
3.  In the n8n app, click **Execute workflow**.
4.  You will see the loop run, and you should receive emails with the PDF reports attached.
5.  To verify the data was saved, go to your `psql` shell and run:
    ```sql
    SELECT id, investor_name, email, report_id, report_generated_at FROM investors;
    ```
    You will see the `report_id` and `report_generated_at` columns are now filled with data.