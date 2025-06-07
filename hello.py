from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import psycopg2
import psycopg2.extras
import traceback
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from werkzeug.exceptions import HTTPException
import socket
import uuid
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Required for flash messages
app.config['GOOGLE_MAPS_API_KEY'] = 'AIzaSyC50DKNKpdKN5edkt94hX-d1EVD1QJUqmY'  # Add Google Maps API key to app config

# Email configuration
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'yeshwanth9750@gmail.com',  # Replace with your email
    'sender_password': 'ivqj logq ilma szuq'   # Replace with your app password
}

# Database connection parameters
DB_PARAMS = {
    "database": "postgres",
    "user": "postgres",
    "password": "1234",
    "host": "localhost",
    "port": "5432"
}

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        try:
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
            server.quit()
            return True
        except smtplib.SMTPAuthenticationError:
            print("Email authentication failed")
            return False
        except smtplib.SMTPException as e:
            print(f"SMTP error: {str(e)}")
            return False
        except socket.gaierror:
            print("Network error while sending email")
            return False
    except Exception as e:
        print(f"Email sending error: {str(e)}")
        return False

# Function to get database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except psycopg2.OperationalError as e:
        print(f"Database connection error: {str(e)}")
        raise Exception("Unable to connect to the database. Please try again later.")
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        raise Exception("An error occurred while connecting to the database.")

# Create the users table if it doesn't exist
def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create users table if it doesn't exist
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password VARCHAR(120) NOT NULL,
                profile_picture VARCHAR(255) DEFAULT 'default_profile.png',
                email VARCHAR(120)
            )
        ''')
        
        # Add profile_picture column if it doesn't exist
        cur.execute('''
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name = 'profile_picture'
                ) THEN
                    ALTER TABLE users 
                    ADD COLUMN profile_picture VARCHAR(255) DEFAULT 'default_profile.png';
                END IF;
            END $$;
        ''')
        
        # Add email column to users table if it doesn't exist
        cur.execute('''
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name = 'email'
                ) THEN
                    ALTER TABLE users 
                    ADD COLUMN email VARCHAR(120);
                END IF;
            END $$;
        ''')
        
        # Create employees table if it doesn't exist
        cur.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                emp_id VARCHAR(20) UNIQUE NOT NULL,
                password VARCHAR(120) NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                role VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add phone column to employees table if it doesn't exist
        cur.execute('''
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'employees' 
                    AND column_name = 'phone_number'
                ) THEN
                    ALTER TABLE employees 
                    ADD COLUMN phone_number VARCHAR(15);
                END IF;
            END $$;
        ''')
        
        # Create savings_accounts table if it doesn't exist
        cur.execute('''
            CREATE TABLE IF NOT EXISTS savings_accounts (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) REFERENCES users(username),
                full_name VARCHAR(100) NOT NULL,
                address TEXT NOT NULL,
                phone VARCHAR(15) NOT NULL,
                initial_deposit DECIMAL(10,2) NOT NULL,
                account_number VARCHAR(20) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username)
            )
        ''')
        
        # Remove email column from savings_accounts table if it exists (now stored in users table)
        cur.execute('''
            DO $$ 
            BEGIN 
                IF EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'savings_accounts' 
                    AND column_name = 'email'
                ) THEN
                    ALTER TABLE savings_accounts 
                    DROP COLUMN email;
                END IF;
            END $$;
        ''')
        
        # Create transactions table if it doesn't exist
        cur.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) REFERENCES users(username),
                amount DECIMAL(10,2) NOT NULL,
                type VARCHAR(10) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create parcels table if it doesn't exist
        cur.execute('''
            CREATE TABLE IF NOT EXISTS parcels (
                id SERIAL PRIMARY KEY,
                tracking_number VARCHAR(20) UNIQUE NOT NULL,
                sender_username VARCHAR(80) REFERENCES users(username),
                receiver_name VARCHAR(100) NOT NULL,
                receiver_phone VARCHAR(15) NOT NULL,
                receiver_address TEXT NOT NULL,
                receiver_pincode VARCHAR(10) NOT NULL,
                parcel_type VARCHAR(20) NOT NULL,
                weight DECIMAL(10,2) NOT NULL,
                dimensions VARCHAR(20) NOT NULL,
                is_fragile BOOLEAN NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                estimated_delivery_date TIMESTAMP NOT NULL,
                latitude DECIMAL(10,8),
                longitude DECIMAL(11,8)
            )
        ''')
        
        # Alter status column in parcels table to VARCHAR(50) if it's smaller (e.g., VARCHAR(20))
        cur.execute('''
            DO $$ 
            BEGIN 
                IF EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'parcels' 
                    AND column_name = 'status'
                    AND character_maximum_length < 50
                ) THEN
                    ALTER TABLE parcels 
                    ALTER COLUMN status TYPE VARCHAR(50);
                END IF;
            END $$;
        ''')
        
        # Add assigned_to_emp_id column to parcels table if it doesn't exist
        cur.execute('''
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'parcels' 
                    AND column_name = 'assigned_to_emp_id'
                ) THEN
                    ALTER TABLE parcels 
                    ADD COLUMN assigned_to_emp_id VARCHAR(20) REFERENCES employees(emp_id);
                END IF;
            END $$;
        ''')
        
        # Check if default employee exists, if not create one
        cur.execute('SELECT * FROM employees WHERE emp_id = %s', ('EMP001',))
        if not cur.fetchone():
            cur.execute('''
                INSERT INTO employees (emp_id, password, full_name, role, phone_number)
                VALUES ('EMP001', 'admin123', 'Admin User', 'Manager', '9876543210')
            ''')
        
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup')
def signup_page():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('index.html')

@app.route('/home')
def home():
    if 'username' not in session:
        return render_template('error.html', 
                             error_type='auth',
                             error_message="Please login to access this page")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Fetch user's profile picture and savings account details, including email from users table
        cur.execute('''
            SELECT u.profile_picture, u.email, s.full_name, s.account_number, s.initial_deposit, s.created_at 
            FROM users u
            LEFT JOIN savings_accounts s ON u.username = s.username
            WHERE u.username = %s
        ''', (session['username'],))
        
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        account_details = None
        if result and result['account_number']:  # Check if user has a savings account
            account_details = {
                'profile_picture': result['profile_picture'],
                'full_name': result['full_name'],
                'account_number': result['account_number'],
                'balance': float(result['initial_deposit']) if result['initial_deposit'] is not None else 0.0,
                'created_at': result['created_at'].strftime('%B %d, %Y') if result['created_at'] else 'N/A'
            }
        
        return render_template('home.html', 
                             username=session['username'],
                             account_details=account_details,
                             user_email=result['email'] if result and 'email' in result else None)
                             
    except Exception as e:
        print(f"Error fetching account details: {str(e)}")
        print(traceback.format_exc())
        return render_template('error.html',
                             error_type='db',
                             error_message="Unable to fetch your account details",
                             error_details=str(e))

@app.route('/create_account')
def create_account_page():
    if 'username' not in session:
        return render_template('error.html',
                             error_type='auth',
                             error_message="Please login to create an account")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Check if user already has an account
        cur.execute('SELECT * FROM savings_accounts WHERE username = %s', (session['username'],))
        existing_account = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if existing_account:
            return redirect(url_for('home'))
            
        return render_template('create_account.html')
        
    except Exception as e:
        print(f"Error checking account status: {str(e)}")
        print(traceback.format_exc())
        return render_template('error.html',
                             error_type='db',
                             error_message="Unable to check account status",
                             error_details=str(e))

@app.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            print(f"Attempting to register user: {username}")

            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            try:
                # Check if user already exists
                cur.execute('SELECT * FROM users WHERE username = %s', (username,))
                user = cur.fetchone()

                if user:
                    return jsonify({
                        'success': False,
                        'message': 'Username already exists!'
                    })
                else:
                    # Create new user
                    cur.execute(
                        'INSERT INTO users (username, password) VALUES (%s, %s)',
                        (username, password)
                    )
                    conn.commit()
                    print(f"Successfully registered user: {username}")
                    session['username'] = username
                    return jsonify({
                        'success': True,
                        'message': 'Successfully registered!',
                        'redirect': url_for('home')
                    })

            except Exception as e:
                conn.rollback()
                print(f"Database operation error: {str(e)}")
                print(traceback.format_exc())
                return jsonify({
                    'success': False,
                    'message': f'Database error: {str(e)}'
                })

            finally:
                cur.close()
                conn.close()

        except Exception as e:
            print(f"General error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            print(f"Attempting to login user: {username}")

            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            try:
                # Check if user exists and password matches
                cur.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
                user = cur.fetchone()

                if user:
                    session['username'] = username
                    return jsonify({
                        'success': True,
                        'message': 'Login successful!',
                        'redirect': url_for('home')
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid username or password!'
                    })

            except Exception as e:
                print(f"Database operation error: {str(e)}")
                print(traceback.format_exc())
                return jsonify({
                    'success': False,
                    'message': f'Database error: {str(e)}'
                })

            finally:
                cur.close()
                conn.close()

        except Exception as e:
            print(f"General error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })

@app.route('/create_savings_account', methods=['POST'])
def create_savings_account():
    if 'username' not in session:
        return jsonify({
            'success': False,
            'message': 'Please login first'
        })

    try:
        data = request.get_json()
        username = session['username']
        
        print(f"Creating savings account for user: {username}")
        print(f"Received data: {data}")
        
        # Validate required fields
        required_fields = ['fullName', 'address', 'phone', 'initialDeposit']
        for field in required_fields:
            if field not in data:
                print(f"Missing required field: {field}")
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                })

        # Validate initial deposit
        try:
            initial_deposit = float(data['initialDeposit'])
            if initial_deposit < 500:
                return jsonify({
                    'success': False,
                    'message': 'Initial deposit must be at least ₹500'
                })
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid initial deposit amount'
            })

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        try:
            # Check if user already has a savings account
            cur.execute('SELECT * FROM savings_accounts WHERE username = %s', (username,))
            existing_account = cur.fetchone()

            if existing_account:
                print(f"User {username} already has an account")
                return jsonify({
                    'success': False,
                    'message': 'You already have a savings account'
                })

            # Generate account number (format: PSA + timestamp + random 4 digits)
            timestamp = datetime.now().strftime('%y%m%d%H%M')
            import random
            random_digits = ''.join([str(random.randint(0, 9)) for _ in range(4)])
            account_number = f'PSA{timestamp}{random_digits}'

            print(f"Generated account number: {account_number}")

            # Create new savings account (without email column)
            cur.execute('''
                INSERT INTO savings_accounts 
                (username, full_name, address, phone, initial_deposit, account_number)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            ''', (
                username,
                data['fullName'],
                data['address'],
                data['phone'],
                initial_deposit,
                account_number
            ))
            
            new_account = cur.fetchone()
            print(f"Created new account: {new_account}")
            
            conn.commit()

            return jsonify({
                'success': True,
                'message': f'Savings account created successfully! Your account number is: {account_number}.'
            })

        except Exception as e:
            conn.rollback()
            print(f"Database operation error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Database error: {str(e)}'
            })

        finally:
            cur.close()
            conn.close()

    except Exception as e:
        print(f"General error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@app.route('/process_transaction', methods=['POST'])
def process_transaction():
    if 'username' not in session:
        return jsonify({
            'success': False,
            'message': 'Please login first'
        })

    try:
        data = request.get_json()
        username = session['username']
        
        # Validate required fields
        required_fields = ['amount', 'type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                })

        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({
                    'success': False,
                    'message': 'Amount must be greater than 0'
                })
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid amount'
            })

        # Validate transaction type
        if data['type'] not in ['deposit', 'withdraw']:
            return jsonify({
                'success': False,
                'message': 'Invalid transaction type'
            })

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        try:
            # Get current balance and account details
            cur.execute('''
                SELECT s.initial_deposit, s.full_name, u.email, s.account_number
                FROM savings_accounts s
                JOIN users u ON s.username = u.username
                WHERE s.username = %s
            ''', (username,))
            
            account = cur.fetchone()
            if not account:
                return jsonify({
                    'success': False,
                    'message': 'Account not found'
                })

            current_balance = float(account['initial_deposit'])
            user_name = account['full_name']
            user_email = account['email']
            account_number = account['account_number']

            # Check if withdrawal is possible
            if data['type'] == 'withdraw' and amount > current_balance:
                return jsonify({
                    'success': False,
                    'message': 'Insufficient balance'
                })

            # Calculate new balance
            new_balance = current_balance + amount if data['type'] == 'deposit' else current_balance - amount

            # Update balance
            cur.execute('''
                UPDATE savings_accounts 
                SET initial_deposit = %s 
                WHERE username = %s
                RETURNING initial_deposit
            ''', (new_balance, username))
            
            updated_balance = cur.fetchone()['initial_deposit']

            # Record transaction
            cur.execute('''
                INSERT INTO transactions 
                (username, amount, type, description)
                VALUES (%s, %s, %s, %s)
            ''', (
                username,
                amount,
                data['type'],
                data.get('description', '')
            ))
            
            conn.commit()

            # Send email notification if user has email
            if user_email:
                transaction_type = "Deposit" if data['type'] == 'deposit' else "Withdrawal"
                email_subject = f"Transaction Alert: {transaction_type} of ₹{amount:.2f}"
                
                email_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #1a237e;">Transaction Alert</h2>
                        <p>Dear {user_name},</p>
                        <p>A {transaction_type.lower()} has been processed on your account. Here are the details:</p>
                        
                        <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <p><strong>Account Number:</strong> {account_number}</p>
                            <p><strong>Transaction Type:</strong> {transaction_type}</p>
                            <p><strong>Amount:</strong> ₹{amount:.2f}</p>
                            <p><strong>Previous Balance:</strong> ₹{current_balance:.2f}</p>
                            <p><strong>New Balance:</strong> ₹{float(updated_balance):.2f}</p>
                            <p><strong>Transaction Time:</strong> {datetime.now().strftime('%B %d, %Y %H:%M:%S')}</p>
                        </div>
                        
                        <p>If you did not authorize this transaction, please contact us immediately.</p>
                        
                        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                            <p style="color: #666; font-size: 14px;">This is an automated message, please do not reply.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                if send_email(user_email, email_subject, email_body):
                    print(f"Transaction notification email sent to {user_email}")
                else:
                    print(f"Failed to send transaction notification email to {user_email}")

            return jsonify({
                'success': True,
                'message': f'Transaction successful! New balance: ₹{float(updated_balance):.2f}',
                'new_balance': float(updated_balance)
            })

        except Exception as e:
            conn.rollback()
            print(f"Database operation error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Database error: {str(e)}'
            })

        finally:
            cur.close()
            conn.close()

    except Exception as e:
        print(f"General error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/employee_login')
def employee_login():
    # Handle URL-based authentication
    auth = request.args.get('auth')
    if not auth:
        return jsonify({
            'success': False,
            'message': 'Authentication required'
        })
    
    try:
        emp_id, password = auth.split('@')
        
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # Check if employee exists and password matches
            cur.execute('SELECT * FROM employees WHERE emp_id = %s AND password = %s', (emp_id, password))
            employee = cur.fetchone()

            if employee:
                session['emp_id'] = emp_id
                session['emp_name'] = employee['full_name']
                session['emp_role'] = employee['role']
                return redirect(url_for('employee_dashboard'))
            else:
                return jsonify({
                    'success': False,
                    'message': 'Invalid employee ID or password!'
                })

        except Exception as e:
            print(f"Employee login error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
        finally:
            cur.close()
            conn.close()
            
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid authentication format. Use: empid@password'
        })

@app.route('/employee_dashboard')
def employee_dashboard():
    if 'emp_id' not in session:
        return redirect(url_for('employee_login'))
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        accounts_list = []
        parcels_list = []
        delivery_agents = []

        if session['emp_role'] == 'Postmaster':
            # Fetch all parcels for Postmaster
            cur.execute('''
                SELECT p.*, e.full_name AS assigned_agent_name, e.phone_number AS assigned_agent_phone
                FROM parcels p
                LEFT JOIN employees e ON p.assigned_to_emp_id = e.emp_id
                ORDER BY p.created_at DESC
            ''')
            all_parcels = cur.fetchall()
            for parcel in all_parcels:
                # Safely convert date strings to datetime objects if necessary
                created_at_dt = parcel['created_at']
                if isinstance(created_at_dt, str):
                    try:
                        created_at_dt = datetime.fromisoformat(created_at_dt.replace('Z', '+00:00'))
                    except ValueError:
                        created_at_dt = None

                estimated_delivery_date_dt = parcel['estimated_delivery_date']
                if isinstance(estimated_delivery_date_dt, str):
                    try:
                        estimated_delivery_date_dt = datetime.fromisoformat(estimated_delivery_date_dt.replace('Z', '+00:00'))
                    except ValueError:
                        estimated_delivery_date_dt = None

                # Safely convert numeric values
                weight = None
                if parcel['weight'] is not None:
                    try:
                        weight = float(parcel['weight'])
                    except (ValueError, TypeError):
                        weight = None

                latitude = None
                if parcel['latitude'] is not None:
                    try:
                        latitude = float(parcel['latitude'])
                    except (ValueError, TypeError):
                        latitude = None

                longitude = None
                if parcel['longitude'] is not None:
                    try:
                        longitude = float(parcel['longitude'])
                    except (ValueError, TypeError):
                        longitude = None

                parcels_list.append({
                    'tracking_number': parcel['tracking_number'],
                    'sender_username': parcel['sender_username'],
                    'receiver_name': parcel['receiver_name'],
                    'receiver_address': parcel['receiver_address'],
                    'receiver_pincode': parcel['receiver_pincode'],
                    'parcel_type': parcel['parcel_type'],
                    'weight': weight,
                    'dimensions': parcel['dimensions'],
                    'is_fragile': parcel['is_fragile'],
                    'status': parcel['status'],
                    'created_at': created_at_dt.strftime('%B %d, %Y %H:%M:%S') if created_at_dt else 'N/A',
                    'estimated_delivery_date': estimated_delivery_date_dt.strftime('%B %d, %Y') if estimated_delivery_date_dt else 'N/A',
                    'latitude': latitude,
                    'longitude': longitude,
                    'assigned_to_emp_id': parcel['assigned_to_emp_id'],
                    'assigned_agent_name': parcel['assigned_agent_name'],
                    'assigned_agent_phone': parcel['assigned_agent_phone']
                })

            # Fetch Delivery Agents
            cur.execute('''
                SELECT emp_id, full_name, phone_number
                FROM employees
                WHERE role = 'Delivery Agent'
                ORDER BY full_name
            ''')
            all_delivery_agents = cur.fetchall()
            for agent in all_delivery_agents:
                delivery_agents.append({
                    'emp_id': agent['emp_id'],
                    'full_name': agent['full_name'],
                    'phone': agent['phone_number']
                })

        elif session['emp_role'] == 'Delivery Agent':
            # Fetch parcels assigned to this specific Delivery Agent
            cur.execute('''
                SELECT p.*, e.full_name AS assigned_agent_name, e.phone_number AS assigned_agent_phone
                FROM parcels p
                LEFT JOIN employees e ON p.assigned_to_emp_id = e.emp_id
                WHERE p.assigned_to_emp_id = %s
                ORDER BY p.created_at DESC
            ''', (session['emp_id'],))
            assigned_parcels = cur.fetchall()
            for parcel in assigned_parcels:
                # Safely convert date strings to datetime objects if necessary
                created_at_dt = parcel['created_at']
                if isinstance(created_at_dt, str):
                    try:
                        created_at_dt = datetime.fromisoformat(created_at_dt.replace('Z', '+00:00'))
                    except ValueError:
                        created_at_dt = None

                estimated_delivery_date_dt = parcel['estimated_delivery_date']
                if isinstance(estimated_delivery_date_dt, str):
                    try:
                        estimated_delivery_date_dt = datetime.fromisoformat(estimated_delivery_date_dt.replace('Z', '+00:00'))
                    except ValueError:
                        estimated_delivery_date_dt = None

                # Safely convert numeric values
                weight = None
                if parcel['weight'] is not None:
                    try:
                        weight = float(parcel['weight'])
                    except (ValueError, TypeError):
                        weight = None

                latitude = None
                if parcel['latitude'] is not None:
                    try:
                        latitude = float(parcel['latitude'])
                    except (ValueError, TypeError):
                        latitude = None

                longitude = None
                if parcel['longitude'] is not None:
                    try:
                        longitude = float(parcel['longitude'])
                    except (ValueError, TypeError):
                        longitude = None

                parcels_list.append({
                    'tracking_number': parcel['tracking_number'],
                    'sender_username': parcel['sender_username'],
                    'receiver_name': parcel['receiver_name'],
                    'receiver_address': parcel['receiver_address'],
                    'receiver_pincode': parcel['receiver_pincode'],
                    'parcel_type': parcel['parcel_type'],
                    'weight': weight,
                    'dimensions': parcel['dimensions'],
                    'is_fragile': parcel['is_fragile'],
                    'status': parcel['status'],
                    'created_at': created_at_dt.strftime('%B %d, %Y %H:%M:%S') if created_at_dt else 'N/A',
                    'estimated_delivery_date': estimated_delivery_date_dt.strftime('%B %d, %Y') if estimated_delivery_date_dt else 'N/A',
                    'latitude': latitude,
                    'longitude': longitude,
                    'assigned_to_emp_id': parcel['assigned_to_emp_id'],
                    'assigned_agent_name': parcel['assigned_agent_name'],
                    'assigned_agent_phone': parcel['assigned_agent_phone']
                })
        else:
            # Existing logic for other employee roles (e.g., Managers viewing accounts)
            cur.execute('''
                SELECT s.*, u.email
                FROM savings_accounts s
                JOIN users u ON s.username = u.username
                ORDER BY s.created_at DESC
            ''')
            accounts = cur.fetchall()
            
            for account in accounts:
                print(f"Processing account: {account}") # Added for debugging
                cur.execute('''
                    SELECT COALESCE(SUM(CASE 
                        WHEN t.type = 'deposit' THEN t.amount 
                        WHEN t.type = 'withdraw' THEN -t.amount 
                    END), 0) as balance
                    FROM transactions t
                    WHERE t.username = %s
                ''', (account['username'],))
                
                transaction_balance = cur.fetchone()['balance'] or 0
                current_balance = float(account['initial_deposit']) + float(transaction_balance)
                
                accounts_list.append({
                    'account_number': account['account_number'],
                    'username': account['username'],
                    'full_name': account['full_name'],
                    'email': account.get('email'), # Safely access email
                    'phone': account['phone'],
                    'address': account['address'],
                    'initial_deposit': float(account['initial_deposit']),
                    'current_balance': current_balance,
                    'created_at': account['created_at'].strftime('%B %d, %Y')
                })
        
        cur.close()
        conn.close()
        
        return render_template('employee_dashboard.html',
                             emp_name=session['emp_name'],
                             emp_role=session['emp_role'],
                             accounts=accounts_list,
                             parcels=parcels_list,
                             delivery_agents=delivery_agents)
                             
    except Exception as e:
        print(f"Error fetching data for employee dashboard: {str(e)}")
        print(traceback.format_exc())
        return render_template('employee_dashboard.html',
                             emp_name=session['emp_name'],
                             emp_role=session['emp_role'],
                             accounts=[],
                             parcels=[],
                             delivery_agents=[],
                             error_message="An error occurred while fetching dashboard data.")

@app.route('/assign_parcel', methods=['POST'])
def assign_parcel():
    if 'emp_id' not in session or session['emp_role'] != 'Postmaster':
        return jsonify({
            'success': False,
            'message': 'Unauthorized access.'
        }), 403

    try:
        data = request.get_json()
        tracking_number = data.get('tracking_number')
        delivery_agent_id = data.get('delivery_agent_id')

        if not tracking_number or not delivery_agent_id:
            return jsonify({
                'success': False,
                'message': 'Tracking number and delivery agent ID are required.'
            }), 400

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Check if parcel is already assigned or delivered
            cur.execute('''
                SELECT status FROM parcels WHERE tracking_number = %s
            ''', (tracking_number,))
            parcel_status = cur.fetchone()

            if parcel_status and parcel_status[0] in ['Assigned to Postman', 'Shipment Initiated', 'On the way to the Post-Office', 'On the way to the receiver location', 'Received']:
                conn.rollback()
                return jsonify({
                    'success': False,
                    'message': 'Parcel is already assigned or in transit.'
                }), 400

            # Update parcel status and assign to delivery agent
            cur.execute('''
                UPDATE parcels
                SET status = 'Assigned to Postman', assigned_to_emp_id = %s
                WHERE tracking_number = %s
                RETURNING tracking_number
            ''', (delivery_agent_id, tracking_number))
            
            updated_parcel = cur.fetchone()
            conn.commit()

            if updated_parcel:
                return jsonify({
                    'success': True,
                    'message': f'Parcel {tracking_number} assigned successfully to {delivery_agent_id}.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Parcel not found.'
                }), 404

        except Exception as e:
            conn.rollback()
            print(f"Database operation error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Database error: {str(e)}'
            }), 500

        finally:
            cur.close()
            conn.close()

    except Exception as e:
        print(f"General error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.route('/pick_up_parcel', methods=['POST'])
def pick_up_parcel():
    if 'emp_id' not in session or session['emp_role'] != 'Delivery Agent':
        return jsonify({
            'success': False,
            'message': 'Unauthorized access.'
        }), 403
    
    try:
        data = request.get_json()
        tracking_number = data.get('tracking_number')

        if not tracking_number:
            return jsonify({
                'success': False,
                'message': 'Tracking number is required.'
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Check if parcel is assigned to this agent and is in 'Assigned to Postman' status
            cur.execute('''
                SELECT status FROM parcels 
                WHERE tracking_number = %s AND assigned_to_emp_id = %s
            ''', (tracking_number, session['emp_id']))
            parcel_info = cur.fetchone()

            if not parcel_info:
                return jsonify({
                    'success': False,
                    'message': 'Parcel not found or not assigned to you.'
                }), 404
            
            if parcel_info[0] != 'Assigned to Postman':
                return jsonify({
                    'success': False,
                    'message': f'Parcel status is {parcel_info[0]}, cannot pick up.'
                }), 400

            # Update status to Shipment Initiated
            cur.execute('''
                UPDATE parcels
                SET status = 'Shipment Initiated'
                WHERE tracking_number = %s AND assigned_to_emp_id = %s
                RETURNING tracking_number
            ''', (tracking_number, session['emp_id']))
            
            updated_parcel = cur.fetchone()
            conn.commit()

            if updated_parcel:
                return jsonify({
                    'success': True,
                    'message': f'Parcel {tracking_number} picked up successfully. Status updated to Shipment Initiated.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to pick up parcel.'
                }), 500

        except Exception as e:
            conn.rollback()
            print(f"Database operation error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Database error: {str(e)}'
            }), 500

        finally:
            cur.close()
            conn.close()

    except Exception as e:
        print(f"General error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.route('/update_parcel_status', methods=['POST'])
def update_parcel_status():
    if 'emp_id' not in session or session['emp_role'] != 'Delivery Agent':
        return jsonify({
            'success': False,
            'message': 'Unauthorized access.'
        }), 403
    
    try:
        data = request.get_json()
        tracking_number = data.get('tracking_number')
        new_status = data.get('new_status')

        if not tracking_number or not new_status:
            return jsonify({
                'success': False,
                'message': 'Tracking number and new status are required.'
            }), 400
        
        # Define allowed status transitions for a delivery agent
        allowed_statuses = [
            'Shipment Initiated',
            'On the way to the Post-Office',
            'On the way to the receiver location',
            'Received'
        ]

        if new_status not in allowed_statuses:
            return jsonify({
                'success': False,
                'message': 'Invalid status update.'
            }), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        try:
            # Check if parcel is assigned to this agent and get sender's email
            cur.execute('''
                SELECT p.*, u.email as sender_email, s.full_name as sender_name
                FROM parcels p
                JOIN users u ON p.sender_username = u.username
                LEFT JOIN savings_accounts s ON u.username = s.username
                WHERE p.tracking_number = %s AND p.assigned_to_emp_id = %s
            ''', (tracking_number, session['emp_id']))
            parcel_info = cur.fetchone()

            if not parcel_info:
                print(f"Parcel {tracking_number} not found or not assigned to employee {session['emp_id']}")
                return jsonify({
                    'success': False,
                    'message': 'Parcel not found or not assigned to you.'
                }), 404
            
            current_status = parcel_info['status']
            print(f"Current status for parcel {tracking_number}: {current_status}")

            # Prevent updating to a status earlier than current or already received/delivered
            if current_status == 'Received' or current_status == new_status:
                return jsonify({
                    'success': False,
                    'message': f'Parcel is already {current_status} or has already reached this status.'
                }), 400
            
            # Simple sequential check for status updates
            status_order = {
                'Assigned to Postman': 0,
                'Shipment Initiated': 1,
                'On the way to the Post-Office': 2,
                'On the way to the receiver location': 3,
                'Received': 4
            }

            if status_order.get(new_status, -1) <= status_order.get(current_status, -1):
                return jsonify({
                    'success': False,
                    'message': 'Invalid status transition.'
                }), 400

            # Update parcel status
            cur.execute('''
                UPDATE parcels
                SET status = %s
                WHERE tracking_number = %s AND assigned_to_emp_id = %s
                RETURNING tracking_number
            ''', (new_status, tracking_number, session['emp_id']))
            
            updated_parcel = cur.fetchone()
            conn.commit()

            if updated_parcel:
                # Send email notification to sender if they have an email
                sender_email = parcel_info['sender_email']
                sender_name = parcel_info['sender_name'] or 'Valued Customer'
                print(f"Attempting to send email for parcel {tracking_number} to {sender_email} (Sender: {sender_name})")

                if sender_email:
                    email_subject = f"Parcel Status Update: {tracking_number}"
                    
                    # Create a more detailed status message
                    status_messages = {
                        'Shipment Initiated': 'Your parcel has been picked up by the delivery agent.',
                        'On the way to the Post-Office': 'Your parcel is being transported to the post office.',
                        'On the way to the receiver location': 'Your parcel is out for delivery to the receiver.',
                        'Received': 'Your parcel has been successfully delivered to the receiver.'
                    }
                    
                    status_message = status_messages.get(new_status, f'Your parcel status has been updated to: {new_status}')
                    
                    email_body = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                            <h2 style="color: #1a237e;">Parcel Status Update</h2>
                            <p>Dear {sender_name},</p>
                            
                            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                                <p><strong>Tracking Number:</strong> {tracking_number}</p>
                                <p><strong>New Status:</strong> {new_status}</p>
                                <p><strong>Update:</strong> {status_message}</p>
                                <p><strong>Receiver:</strong> {parcel_info['receiver_name']}</p>
                                <p><strong>Delivery Address:</strong><br>{parcel_info['receiver_address']}<br>Pincode: {parcel_info['receiver_pincode']}</p>
                            </div>
                            
                            <p>You can track your parcel's status anytime through your dashboard.</p>
                            
                            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                                <p style="color: #666; font-size: 14px;">This is an automated message, please do not reply.</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    if send_email(sender_email, email_subject, email_body):
                        print(f"Status update email sent successfully to {sender_email} for parcel {tracking_number}")
                    else:
                        print(f"Failed to send status update email to {sender_email} for parcel {tracking_number}")
                else:
                    print(f"Sender email not available for parcel {tracking_number}. Skipping email notification.")

                return jsonify({
                    'success': True,
                    'message': f'Parcel {tracking_number} status updated to {new_status}.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to update parcel status.'
                }), 500

        except Exception as e:
            conn.rollback()
            print(f"Database operation error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Database error: {str(e)}'
            }), 500

        finally:
            cur.close()
            conn.close()

    except Exception as e:
        print(f"General error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.route('/user_dashboard')
def user_dashboard():
    if 'username' not in session:
        return render_template('error.html',
                             error_type='auth',
                             error_message="Please login to access your dashboard")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Fetch user's profile picture and savings account details
        cur.execute('''
            SELECT u.profile_picture, u.email, s.full_name, s.account_number, s.initial_deposit, s.created_at 
            FROM users u
            LEFT JOIN savings_accounts s ON u.username = s.username
            WHERE u.username = %s
        ''', (session['username'],))
        
        result = cur.fetchone()

        print(f"DEBUG: User dashboard result for {session['username']}: {result}")
        
        account_details = None
        if result and result['account_number']:  # Check if user has a savings account
            account_details = {
                'profile_picture': result['profile_picture'],
                'full_name': result['full_name'],
                'account_number': result['account_number'],
                'balance': float(result['initial_deposit']) if result['initial_deposit'] is not None else 0.0,
                'created_at': result['created_at'].strftime('%B %d, %Y') if result['created_at'] else 'N/A'
            }

        # Fetch parcels sent by the user, including assigned postman details
        cur.execute('''
            SELECT p.tracking_number, p.receiver_name, p.receiver_address, p.receiver_pincode, 
                   p.parcel_type, p.weight, p.dimensions, p.status, p.created_at, 
                   p.estimated_delivery_date, e.full_name AS assigned_postman_name, e.phone_number AS assigned_postman_phone
            FROM parcels p
            LEFT JOIN employees e ON p.assigned_to_emp_id = e.emp_id
            WHERE p.sender_username = %s
            ORDER BY p.created_at DESC
        ''', (session['username'],))

        parcels = cur.fetchall()
        parcels_list = []
        for parcel in parcels:
            # Safely convert date strings to datetime objects if necessary
            created_at_dt = parcel['created_at']
            if isinstance(created_at_dt, str):
                try:
                    created_at_dt = datetime.fromisoformat(created_at_dt.replace('Z', '+00:00'))
                except ValueError:
                    created_at_dt = None

            estimated_delivery_date_dt = parcel['estimated_delivery_date']
            if isinstance(estimated_delivery_date_dt, str):
                try:
                    estimated_delivery_date_dt = datetime.fromisoformat(estimated_delivery_date_dt.replace('Z', '+00:00'))
                except ValueError:
                    estimated_delivery_date_dt = None

            parcels_list.append({
                'tracking_number': parcel['tracking_number'],
                'receiver_name': parcel['receiver_name'],
                'receiver_address': parcel['receiver_address'],
                'receiver_pincode': parcel['receiver_pincode'],
                'parcel_type': parcel['parcel_type'],
                'weight': float(parcel['weight']),
                'dimensions': parcel['dimensions'],
                'status': parcel['status'],
                'created_at': created_at_dt.strftime('%B %d, %Y') if created_at_dt else 'N/A',
                'estimated_delivery_date': estimated_delivery_date_dt.strftime('%B %d, %Y') if estimated_delivery_date_dt else 'N/A',
                'assigned_postman_name': parcel['assigned_postman_name'],
                'assigned_postman_phone': parcel['assigned_postman_phone']
            })
        
        cur.close()
        conn.close()
        
        return render_template('user_dashboard.html', 
                             username=session['username'],
                             account_details=account_details,
                             parcels=parcels_list,
                             user_email=result.get('email') if result else None)
                             
    except Exception as e:
        print(f"Error fetching account details: {str(e)}")
        print(traceback.format_exc())
        return render_template('error.html',
                             error_type='db',
                             error_message="Unable to fetch your dashboard details",
                             error_details=str(e))

@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    if 'username' not in session:
        return jsonify({
            'success': False,
            'message': 'Please login first'
        })

    try:
        if 'profile_picture' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No file uploaded'
            })

        file = request.files['profile_picture']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            })

        # Check if the file is an allowed image type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if '.' not in file.filename or \
           file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({
                'success': False,
                'message': 'Invalid file type. Please upload an image (PNG, JPG, JPEG, or GIF)'
            })

        # Create uploads directory if it doesn't exist
        upload_folder = os.path.join('static', 'profile_pictures')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # Generate unique filename
        filename = f"{session['username']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}"
        filepath = os.path.join(upload_folder, filename)

        # Save the file
        file.save(filepath)

        # Update database with new profile picture path
        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute('''
                UPDATE users 
                SET profile_picture = %s 
                WHERE username = %s
            ''', (filename, session['username']))
            
            conn.commit()

            return jsonify({
                'success': True,
                'message': 'Profile picture updated successfully',
                'profile_picture': filename
            })

        except Exception as e:
            conn.rollback()
            print(f"Database error: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Failed to update profile picture in database'
            })

        finally:
            cur.close()
            conn.close()

    except Exception as e:
        print(f"Error uploading profile picture: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while uploading the profile picture'
        })

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'emp_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Please login as an employee first'
        })

    try:
        data = request.get_json()
        account_number = data.get('account_number')

        if not account_number:
            return jsonify({
                'success': False,
                'message': 'Account number is required'
            })

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        try:
            # First check if the account exists and has zero or negative balance
            cur.execute('''
                SELECT s.*, u.email, u.username,
                       COALESCE(SUM(CASE 
                           WHEN t.type = 'deposit' THEN t.amount 
                           WHEN t.type = 'withdraw' THEN -t.amount 
                       END), 0) as transaction_balance
                FROM savings_accounts s
                JOIN users u ON s.username = u.username
                LEFT JOIN transactions t ON s.username = t.username
                WHERE s.account_number = %s
                GROUP BY s.id, u.email, u.username
            ''', (account_number,))
            
            account = cur.fetchone()
            
            if not account:
                return jsonify({
                    'success': False,
                    'message': 'Account not found'
                })

            current_balance = float(account['initial_deposit']) + float(account['transaction_balance'])
            
            if current_balance > 0:
                return jsonify({
                    'success': False,
                    'message': 'Cannot delete account with positive balance'
                })

            # Get the username and email before deleting the account
            username = account['username']
            user_email = account['email']

            # --- Handle profile picture deletion ---
            cur.execute('''
                SELECT profile_picture FROM users WHERE username = %s
            ''', (username,))
            user_info = cur.fetchone()
            
            if user_info and user_info['profile_picture'] and user_info['profile_picture'] != 'default_profile.png':
                old_profile_picture_path = os.path.join('static', 'profile_pictures', user_info['profile_picture'])
                if os.path.exists(old_profile_picture_path):
                    try:
                        os.remove(old_profile_picture_path)
                        print(f"Deleted old profile picture: {old_profile_picture_path}")
                    except OSError as e:
                        print(f"Error deleting profile picture {old_profile_picture_path}: {e}")
                
                # Set profile picture back to default in the database
                cur.execute('''
                    UPDATE users SET profile_picture = 'default_profile.png' WHERE username = %s
                ''', (username,))
                print(f"User {username} profile picture reset to default.")
            # --- End profile picture deletion ---

            # Delete only the savings account and its transactions
            cur.execute('DELETE FROM transactions WHERE username = %s', (username,))
            cur.execute('DELETE FROM savings_accounts WHERE account_number = %s', (account_number,))
            
            conn.commit()

            # Send email notification to user about account deletion
            if user_email:
                email_subject = "Savings Account Deletion Confirmation"
                email_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #1a237e;">Savings Account Deletion Confirmation</h2>
                        <p>Dear {account['full_name']},</p>
                        
                        <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <p>Your savings account has been deleted with the following details:</p>
                            <p><strong>Account Number:</strong> {account_number}</p>
                            <p><strong>Account Holder:</strong> {account['full_name']}</p>
                            <p><strong>Deletion Date:</strong> {datetime.now().strftime('%B %d, %Y %H:%M:%S')}</p>
                        </div>
                        
                        <p>Note: Your user account and email address are still active. You can create a new savings account anytime.</p>
                        
                        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                            <p style="color: #666; font-size: 14px;">This is an automated message, please do not reply.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                if send_email(user_email, email_subject, email_body):
                    print(f"Account deletion notification email sent to {user_email}")
                else:
                    print(f"Failed to send account deletion notification email to {user_email}")

            return jsonify({
                'success': True,
                'message': f'Savings account {account_number} has been deleted successfully'
            })

        except Exception as e:
            conn.rollback()
            print(f"Database operation error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Database error: {str(e)}'
            })

        finally:
            cur.close()
            conn.close()

    except Exception as e:
        print(f"General error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@app.route('/send_parcel')
def send_parcel_page():
    if 'username' not in session:
        return render_template('error.html',
                             error_type='auth',
                             error_message="Please login to send a parcel")
    return render_template('send_parcel.html', google_maps_api_key=app.config['GOOGLE_MAPS_API_KEY'])

@app.route('/send_parcel', methods=['POST'])
def send_parcel():
    if 'username' not in session:
        return jsonify({
            'success': False,
            'message': 'Please login first'
        })

    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['type', 'weight', 'dimensions', 'fragile', 'receiver']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                })

        # Validate receiver details
        receiver_fields = ['name', 'phone', 'address', 'pincode']
        for field in receiver_fields:
            if field not in data['receiver']:
                return jsonify({
                    'success': False,
                    'message': f'Missing receiver field: {field}'
                })

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        try:
            # Generate tracking number (format: PS + timestamp + random 4 digits)
            timestamp = datetime.now().strftime('%y%m%d%H%M')
            import random
            random_digits = ''.join([str(random.randint(0, 9)) for _ in range(4)])
            tracking_number = f'PS{timestamp}{random_digits}'

            # Calculate delivery date (3-5 days for standard, 1-2 days for express)
            delivery_days = 3 if data['type'] != 'express' else 1
            delivery_date = datetime.now() + timedelta(days=delivery_days)

            # Safely get and convert latitude and longitude
            lat_input = data['location'].get('lat') if data.get('location') else None
            lng_input = data['location'].get('lng') if data.get('location') else None

            final_lat = None
            if lat_input is not None and str(lat_input).strip() != '':
                try:
                    final_lat = float(lat_input)
                except (ValueError, TypeError):
                    final_lat = None
            
            final_lng = None
            if lng_input is not None and str(lng_input).strip() != '':
                try:
                    final_lng = float(lng_input)
                except (ValueError, TypeError):
                    final_lng = None

            # Insert parcel details
            cur.execute('''
                INSERT INTO parcels (
                    tracking_number,
                    sender_username,
                    receiver_name,
                    receiver_phone,
                    receiver_address,
                    receiver_pincode,
                    parcel_type,
                    weight,
                    dimensions,
                    is_fragile,
                    status,
                    created_at,
                    estimated_delivery_date,
                    latitude,
                    longitude
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            ''', (
                tracking_number,
                session['username'],
                data['receiver']['name'],
                data['receiver']['phone'],
                data['receiver']['address'],
                data['receiver']['pincode'],
                data['type'],
                float(data['weight']) if data['weight'] and str(data['weight']).strip() != '' else None,
                data['dimensions'],
                data['fragile'] == 'yes',
                'pending',
                datetime.now(),
                delivery_date,
                final_lat,
                final_lng
            ))
            
            new_parcel = cur.fetchone()
            conn.commit()

            # Send email notification if receiver has email
            if data['receiver'].get('email'):
                email_subject = f"Parcel Tracking Number: {tracking_number}"
                email_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #1a237e;">Parcel Tracking Information</h2>
                        <p>Dear {data['receiver']['name']},</p>
                        <p>A parcel has been sent to you. Here are the details:</p>
                        
                        <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <p><strong>Tracking Number:</strong> {tracking_number}</p>
                            <p><strong>Parcel Type:</strong> {data['type'].title()}</p>
                            <p><strong>Weight:</strong> {data['weight']} kg</p>
                            <p><strong>Estimated Delivery:</strong> {delivery_date.strftime('%B %d, %Y')}</p>
                            <p><strong>Delivery Address:</strong><br>{data['receiver']['address']}<br>Pincode: {data['receiver']['pincode']}</p>
                        </div>
                        
                        <p>You can track your parcel using the tracking number above.</p>
                        
                        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                            <p style="color: #666; font-size: 14px;">This is an automated message, please do not reply.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                if send_email(data['receiver']['email'], email_subject, email_body):
                    print(f"Parcel notification email sent to {data['receiver']['email']}")
                else:
                    print(f"Failed to send parcel notification email to {data['receiver']['email']}")

            return jsonify({
                'success': True,
                'message': f'Parcel sent successfully! Tracking number: {tracking_number}',
                'tracking_number': tracking_number
            })

        except Exception as e:
            conn.rollback()
            print(f"Database operation error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Database error: {str(e)}'
            })

        finally:
            cur.close()
            conn.close()

    except Exception as e:
        print(f"General error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@app.route('/delete_parcel', methods=['POST'])
def delete_parcel():
    if 'username' not in session:
        return jsonify({
            'success': False,
            'message': 'Please login first'
        })
    
    try:
        data = request.get_json()
        tracking_number = data.get('tracking_number')

        if not tracking_number:
            return jsonify({
                'success': False,
                'message': 'Tracking number is required'
            })

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        try:
            # Delete the parcel for the logged-in user
            cur.execute('''
                DELETE FROM parcels
                WHERE tracking_number = %s AND sender_username = %s
                RETURNING tracking_number
            ''', (tracking_number, session['username'],))
            
            deleted_parcel = cur.fetchone()
            conn.commit()

            if deleted_parcel:
                return jsonify({
                    'success': True,
                    'message': f'Parcel {tracking_number} deleted successfully.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Parcel not found or you do not have permission to delete it.'
                })

        except Exception as e:
            conn.rollback()
            print(f"Database operation error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Database error: {str(e)}'
            })

        finally:
            cur.close()
            conn.close()

    except Exception as e:
        print(f"General error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@app.route('/update_user_email', methods=['POST'])
def update_user_email():
    if 'username' not in session:
        return jsonify({
            'success': False,
            'message': 'Please login first'
        }), 401
    
    try:
        data = request.get_json()
        new_email = data.get('email', '')
        username = session['username']

        # Basic email validation
        if new_email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', new_email):
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute('''
                UPDATE users
                SET email = %s
                WHERE username = %s
                RETURNING username
            ''', (new_email if new_email else None, username))
            
            updated_user = cur.fetchone()
            conn.commit()

            if updated_user:
                return jsonify({
                    'success': True,
                    'message': 'Email address updated successfully!'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'User not found.'
                }), 404

        except Exception as e:
            conn.rollback()
            print(f"Database operation error (update_user_email): {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Database error: {str(e)}'
            }), 500

        finally:
            cur.close()
            conn.close()

    except Exception as e:
        print(f"General error (update_user_email): {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.errorhandler(HTTPException)
def handle_http_error(e):
    return render_template('error.html', 
                         error_type='network',
                         error_message=str(e),
                         error_details=f"Error code: {e.code}"), e.code

@app.errorhandler(Exception)
def handle_generic_error(e):
    error_type = 'db' if isinstance(e, psycopg2.Error) else 'network'
    return render_template('error.html',
                         error_type=error_type,
                         error_message="An unexpected error occurred",
                         error_details=str(e)), 500

if __name__ == '__main__':
    try:
        init_db()
        app.run(debug=True)
    except Exception as e:
        print(f"Application startup error: {str(e)}")
        print(traceback.format_exc())