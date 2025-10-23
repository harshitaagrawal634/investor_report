# Investor Report Automation Project

This project automatically generates PDF reports for investors, saves them to a database, and emails them. It uses a Python Flask API, a PostgreSQL database, and an n8n workflow.

---

## How It Works

1.  An **n8n workflow** runs on a schedule.
2.  It fetches investor data from a **PostgreSQL database**.
3.  It loops through each investor and calls a **Python Flask API** to generate a custom PDF report.
4.  The API saves the PDF back to the database.
5.  The n8n workflow then downloads the PDF and emails it to the investor.

---

## Local Setup Instructions

To run this project on your local machine, you will need to set up all three components: the Database, the API, and the n8n Workflow.

### 1. Prerequisites

* [PostgreSQL](https://www.postgresql.org/download/) (I used version 17.6)
* [Python 3.10+](https://www.python.org/downloads/)
* [n8n Desktop](https://n8n.io/desktop/)
* [Git](https://git-scm.com/downloads/)

### 2. Database (PostgreSQL) Setup

1.  After installing PostgreSQL, open `psql`.
2.  Create the database:
    ```sql
    CREATE DATABASE my_investors_db;
    ```
3.  Connect to your new database:
    ```sql
    \c my_investors_db
    ```
4.  Create the `investors` table. (You should paste your `CREATE TABLE` command here so they can copy it).
    ```sql
    CREATE TABLE investors (
        id SERIAL PRIMARY KEY,
        investor_name VARCHAR(255),
        email VARCHAR(255),
        total_committed DECIMAL,
        pdf_report BYTEA,
        html_report TEXT,
        report_id VARCHAR(255),
        report_generated_at TIMESTAMP
    );
    ```
5.  (Optional) Insert some test data:
    ```sql
    INSERT INTO investors (investor_name, email) VALUES ('Test User', 'test@example.com');
    ```

### 3. API (Python) Setup

1.  Clone this repository:
    ```bash
    git clone [https://github.com/harshitaagrawal634/your-repo-name.git](https://github.com/harshitaagrawal634/your-repo-name.git)
    cd your-repo-name
    ```
2.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  Install the required libraries:
    ```bash
    pip install -r requirements.txt
    ```
4.  Create your local environment file. **This file is private and should not be on GitHub.**
    * Create a file named `.env`
    * Copy the contents of `.env.example` (if you have one) or add the following, filling in your *local* database details:
    ```ini
    DB_NAME="my_investors_db"
    DB_USER="postgres"
    DB_PASSWORD="your-local-postgres-password"
    DB_HOST="localhost"
    DB_PORT="5432"
    ```
5.  Run the API server:
    ```bash
    python app.py
    ```
    The server should now be running at `http://127.0.0.1:8080/`.

### 4. Automation (n8n) Setup

1.  **Export Your Workflow:**
    * In your local n8n app, open your workflow.
    * Go to **File > Export > Workflow**.
    * Save the `.json` file in this GitHub repository (e.g., `n8n_workflow.json`).
    * (You will need to `git add n8n_workflow.json`, `git commit`, and `git push` this file).

2.  **Import the Workflow:**
    * Open the n8n Desktop app on the new machine.
    * Go to **File > Import > From File...**
    * Select the `n8n_workflow.json` file from this repository.
    * The workflow will appear. You may need to re-select your SMTP credentials in the `Send email` node.