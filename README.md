# Postal Savings Account & Parcel Management System

A comprehensive web application for managing user savings accounts and streamlining parcel delivery operations, featuring secure authentication, financial transactions, real-time parcel tracking, and multi-role employee dashboards.

## ✨ Features

### User Module
*   **Secure User Authentication:** Signup, Login, and Logout functionality for individual users.
*   **Savings Account Management:**
    *   Create and view personal savings account details.
    *   Perform deposits and withdrawals with real-time balance updates.
*   **Profile Management:** Upload and manage profile pictures.
*   **Email Management:** Update and manage email addresses directly from the dashboard.
*   **Parcel Sending & Tracking:**
    *   Send new parcels with details like type, weight, dimensions, and fragility.
    *   Track sent parcels with real-time status updates (Pending, Assigned to Postman, Shipment Initiated, On the way to Post-Office, On the way to Receiver, Received).
    *   View assigned postman details and contact information for parcels.
    *   Delete parcels (only by sender).
*   **Email Notifications:** Receive email alerts for savings account creation, transactions, and parcel status updates.

### Employee Module
*   **Employee Login:** Secure login for different employee roles (Postmaster, Delivery Agent).
*   **Postmaster Dashboard:**
    *   View all user savings accounts and their balances.
    *   Delete savings accounts (if balance is zero or negative).
    *   View all parcels and assign them to specific Delivery Agents.
    *   View all Delivery Agents.
*   **Delivery Agent Dashboard:**
    *   View only parcels assigned to them.
    *   Update parcel status with specific transitions (Pick Up, On the way to Post-Office, On the way to Receiver, Received).

## 🚀 Technologies Used

*   **Backend:** Flask (Python)
*   **Database:** PostgreSQL
*   **Database Driver:** Psycopg2
*   **Frontend:** HTML, CSS, JavaScript
*   **Mapping:** Leaflet.js (for OpenStreetMap integration)
*   **Icons:** Font Awesome
*   **Email Service:** SMTPLib (for sending emails via Gmail SMTP)

## 🛠️ Setup and Installation

Follow these steps to set up the project locally:

### Prerequisites
*   Python 3.8+
*   PostgreSQL installed and running (with default user `postgres` and password `1234` or adjust `DB_PARAMS` in `hello.py`)
*   `pip` (Python package installer)

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd DBMS_Project
```

### 2. Create a Virtual Environment (Recommended)
```bash
python -m venv venv
```

### 3. Activate the Virtual Environment
*   **Windows:**
    ```bash
    .\venv\Scripts\activate
    ```
*   **macOS/Linux:**
    ```bash
    source venv/bin/activate
    ```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```
*(If `requirements.txt` is not present, you can create it with `pip freeze > requirements.txt` after installing `flask`, `psycopg2-binary`, `smtplib`, `werkzeug`, `uuid`, `re`)*
```bash
pip install Flask psycopg2-binary
```

### 5. Database Setup
Ensure your PostgreSQL server is running. The application will initialize the database tables on first run. If you encounter database errors (e.g., "relation does not exist" or "column already exists"), it's best to perform a clean database reset.

**To perform a clean database reset (Recommended for development):**
*   **Using `psql` (command line):**
    1.  Connect to your PostgreSQL server: `psql -U postgres -h localhost -p 5432 -d postgres` (or `template1` if `postgres` is locked).
    2.  Switch to `template1` if connected to `postgres`: `\c template1;`
    3.  Drop the database: `DROP DATABASE IF EXISTS postgres;`
    4.  Create the database: `CREATE DATABASE postgres;`
    5.  Exit `psql`: `\q`
*   **Using pgAdmin:** Delete and then recreate the `postgres` database.

### 6. Configure Email Settings
Open `hello.py` and update the `EMAIL_CONFIG` dictionary with your Gmail SMTP details. You might need to generate an App Password for your Gmail account if you have 2-Factor Authentication enabled.

```python
# hello.py
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'your_email@gmail.com',  # Replace with your email
    'sender_password': 'your_app_password'   # Replace with your app password
}
```

### 7. Run the Application
```bash
python hello.py
```
The application will be accessible at `http://127.0.0.1:5000`.

## 📝 Usage

### User Access
*   **Signup:** Register a new user account.
*   **Login:** Access your user dashboard.
*   **Home (`/home`):** View a summary and navigate to different sections.
*   **User Dashboard (`/user_dashboard`):**
    *   View savings account details (or create one if not existing).
    *   Manage your email address.
    *   Perform deposits and withdrawals.
    *   View and manage your sent parcels.
*   **Send Parcel (`/send_parcel`):** Create and send a new parcel.

### Employee Access
Employees (Postmaster, Delivery Agent) log in via a special URL format:
`http://127.0.0.1:5000/employee_login?auth=<employee_id>@<password>`

**Default Employee:**
*   **Employee ID:** `EMP001`
*   **Password:** `admin123`
*   **Role:** `Manager` (acts as a Postmaster for this application)

*   **Employee Dashboard (`/employee_dashboard`):**
    *   **Postmaster:** View all accounts, delete accounts (if balance <= 0), view all parcels, assign parcels to Delivery Agents, view Delivery Agent details.
    *   **Delivery Agent:** View only assigned parcels, update parcel statuses (Pick Up, On the way to Post-Office, On the way to Receiver, Received).

## 📊 Database Schema

```mermaid
graph TD
    users[users] --- savings_accounts[savings_accounts]
    users --- parcels[parcels]
    users --- transactions[transactions]
    employees[employees] --- parcels

    subgraph User Data
        users
    end

    subgraph Financial
        savings_accounts
        transactions
    end

    subgraph Parcel Logistics
        parcels
        employees
    end

    classDef tableStyle fill:#f9f,stroke:#333,stroke-width:2px;
    class users,savings_accounts,transactions,parcels,employees tableStyle;

    users -- "1:1 or 1:0 (optional)" --> savings_accounts: username
    users -- "1:N" --> parcels: sender_username
    users -- "1:N" --> transactions: username
    employees -- "1:N" --> parcels: assigned_to_emp_id

    users{id, username, password, profile_picture, email}
    savings_accounts{id, username, full_name, address, phone, initial_deposit, account_number, created_at}
    transactions{id, username, amount, type, description, created_at}
    parcels{id, tracking_number, sender_username, receiver_name, receiver_phone, receiver_address, receiver_pincode, parcel_type, weight, dimensions, is_fragile, status, created_at, estimated_delivery_date, latitude, longitude, assigned_to_emp_id}
    employees{id, emp_id, password, full_name, role, created_at, phone_number}

```

## 📂 Project Structure

```
.
├── hello.py                # Main Flask application with routes and database logic
├── requirements.txt        # Python dependencies
├── static/                 # Static files (CSS, JS, images)
│   ├── profile_pictures/   # User profile pictures
│   └── css/                # Stylesheets
│   └── js/                 # JavaScript files
├── templates/              # HTML Jinja2 templates
│   ├── index.html
│   ├── home.html
│   ├── create_account.html
│   ├── user_dashboard.html
│   ├── employee_dashboard.html
│   ├── send_parcel.html
│   └── error.html
└── README.md               # Project README file
```

## 🤝 Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## 📄 License

This project is open-source and available under the MIT License.

## 📧 Contact

For any questions or feedback, please contact [yeshwanth9750@gmail.com]
