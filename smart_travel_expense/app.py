"""
AI Powered Smart Travel Expense Fraud Identifier & Smart Reimbursement Portal
Main Flask Application Server
"""

import os
import sqlite3
import json
from datetime import datetime, date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Import AI Fraud Detection Module
from models.fraud_detection import evaluate_expense_fraud

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'smart_travel_expense_super_secret_key_2026'

# Base Directories
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'txt', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max limit

# Ensure uploads directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if uploaded file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    """Returns a SQLite database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes tables and seeds demo accounts and test data."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            employee_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            department TEXT,
            designation TEXT,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Employee',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Travel Requests Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS travel_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            purpose TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            travel_type TEXT NOT NULL,
            from_date DATE NOT NULL,
            to_date DATE NOT NULL,
            travel_mode TEXT NOT NULL,
            estimated_cost REAL NOT NULL,
            accommodation TEXT,
            advance_required REAL DEFAULT 0,
            description TEXT,
            status TEXT DEFAULT 'Pending',
            manager_comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Expenses Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            trip_id INTEGER,
            expense_date DATE NOT NULL,
            category TEXT NOT NULL,
            merchant TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'INR',
            payment_method TEXT NOT NULL,
            business_purpose TEXT NOT NULL,
            receipt_filename TEXT,
            notes TEXT,
            status TEXT DEFAULT 'Pending',
            manager_decision TEXT DEFAULT 'Pending',
            admin_decision TEXT DEFAULT 'Pending',
            reimbursement_status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. Fraud Results Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fraud_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL,
            risk_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            fraud_reasons TEXT,
            ocr_summary TEXT,
            anomaly_score REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 5. Reimbursements Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reimbursements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL,
            employee_id TEXT NOT NULL,
            approved_amount REAL NOT NULL,
            reimbursement_amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            payment_date DATE NOT NULL,
            transaction_id TEXT NOT NULL,
            comments TEXT,
            status TEXT DEFAULT 'Reimbursed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()

    # Seed Demo Users if database is newly initialized
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        # Create default demo sample receipts in uploads
        sample_receipt_1 = os.path.join(UPLOAD_FOLDER, "receipt_uber_delhi.txt")
        sample_receipt_2 = os.path.join(UPLOAD_FOLDER, "receipt_marriott_stay.txt")
        sample_receipt_3 = os.path.join(UPLOAD_FOLDER, "receipt_suspicious_club.txt")

        with open(sample_receipt_1, "w") as f:
            f.write("UBER RIDES INDIA PVT LTD\nDate: 2026-09-20\nTrip: Airport to Connaught Place\nTotal: INR 850.00\nPayment: UPI\nTax Invoice #UB-982145")

        with open(sample_receipt_2, "w") as f:
            f.write("JW MARRIOTT HOTEL NEW DELHI\nDate: 2026-09-21\nRoom 402 - 2 Nights Stay\nTotal: INR 18,500.00\nPayment: Credit Card\nGSTIN: 07AAACH1234F1Z5")

        with open(sample_receipt_3, "w") as f:
            f.write("LUXURY CASINO & SPA RESORT\nDate: 2026-09-25\nVIP Lounge & Bar Drinks\nTotal: INR 45,000.00\nPayment: Cash")

        # 1. Employee: Alex Rivera
        cursor.execute('''
            INSERT INTO users (name, employee_id, email, phone, department, designation, password, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Alex Rivera',
            'EMP-1001',
            'employee@example.com',
            '+91 98765 01001',
            'Engineering',
            'Lead Systems Architect',
            generate_password_hash('employee123'),
            'Employee'
        ))

        # 2. Manager: Sarah Jenkins
        cursor.execute('''
            INSERT INTO users (name, employee_id, email, phone, department, designation, password, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Sarah Jenkins',
            'MGR-2001',
            'manager@example.com',
            '+91 98765 02001',
            'Engineering',
            'Engineering Director',
            generate_password_hash('manager123'),
            'Manager'
        ))

        # 3. Admin / Finance: David Sterling
        cursor.execute('''
            INSERT INTO users (name, employee_id, email, phone, department, designation, password, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'David Sterling',
            'ADM-3001',
            'admin@example.com',
            '+91 98765 03001',
            'Finance & Auditing',
            'Chief Financial Controller',
            generate_password_hash('admin123'),
            'Admin'
        ))

        # Sample Travel Pre-Approval Requests
        cursor.execute('''
            INSERT INTO travel_requests (employee_id, purpose, source, destination, travel_type, from_date, to_date, travel_mode, estimated_cost, accommodation, advance_required, description, status, manager_comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'EMP-1001',
            'Client Architecture Review & Cloud Migration',
            'Bengaluru',
            'New Delhi',
            'Domestic',
            '2026-09-18',
            '2026-09-23',
            'Flight',
            35000.00,
            'Yes',
            10000.00,
            'Meeting with enterprise banking partner executive team to deploy microservices cluster.',
            'Approved',
            'Approved by Manager Sarah Jenkins. Budget cap ₹35,000.'
        ))
        trip_1_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO travel_requests (employee_id, purpose, source, destination, travel_type, from_date, to_date, travel_mode, estimated_cost, accommodation, advance_required, description, status, manager_comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'EMP-1001',
            'Tech Conference & Developer Keynote',
            'Bengaluru',
            'Mumbai',
            'Domestic',
            '2026-10-10',
            '2026-10-12',
            'Flight',
            22000.00,
            'Yes',
            5000.00,
            'Presenting AI Governance paper at National Software Conclave.',
            'Pending',
            None
        ))

        # Seed Sample Expenses with AI Fraud Results
        # Sample Expense 1: Genuine Clean Expense (Taxi)
        cursor.execute('''
            INSERT INTO expenses (employee_id, trip_id, expense_date, category, merchant, amount, currency, payment_method, business_purpose, receipt_filename, notes, status, manager_decision, admin_decision, reimbursement_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'EMP-1001',
            trip_1_id,
            '2026-09-20',
            'Taxi',
            'Uber Rides India',
            850.00,
            'INR',
            'UPI',
            'Airport transfer to client office in Connaught Place',
            'receipt_uber_delhi.txt',
            'Direct ride from IGI T3',
            'Approved',
            'Approved',
            'Genuine',
            'Reimbursed'
        ))
        exp_1_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO fraud_results (expense_id, risk_score, risk_level, fraud_reasons, ocr_summary, anomaly_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            exp_1_id,
            12,
            'LOW RISK',
            json.dumps(['No anomalies or policy violations detected. Claim aligns with standard parameters.']),
            'Receipt verified (0.3 KB). Vendor & itemization verified.',
            0.15
        ))

        cursor.execute('''
            INSERT INTO reimbursements (expense_id, employee_id, approved_amount, reimbursement_amount, payment_method, payment_date, transaction_id, comments, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            exp_1_id,
            'EMP-1001',
            850.00,
            850.00,
            'UPI Direct Payout',
            '2026-09-22',
            'UPI-981024810294',
            'Processed automatically via corporate payroll pipeline.',
            'Reimbursed'
        ))

        # Sample Expense 2: Clean Hotel Expense (Approved, Pending Reimbursement)
        cursor.execute('''
            INSERT INTO expenses (employee_id, trip_id, expense_date, category, merchant, amount, currency, payment_method, business_purpose, receipt_filename, notes, status, manager_decision, admin_decision, reimbursement_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'EMP-1001',
            trip_1_id,
            '2026-09-21',
            'Hotel',
            'JW Marriott New Delhi',
            18500.00,
            'INR',
            'Corporate Card',
            '2-night accommodation for on-site migration workshop',
            'receipt_marriott_stay.txt',
            'Corporate discounted rate applied',
            'Approved',
            'Approved',
            'Genuine',
            'Pending'
        ))
        exp_2_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO fraud_results (expense_id, risk_score, risk_level, fraud_reasons, ocr_summary, anomaly_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            exp_2_id,
            24,
            'LOW RISK',
            json.dumps([
                'Claimed amount ₹18,500.00 is higher than standard benchmark (₹12,000.00) for Hotel, but within approved pre-authorization limit.'
            ]),
            'Receipt verified (0.4 KB). Vendor & itemization verified.',
            0.08
        ))

        # Sample Expense 3: Flagged High Risk Expense (Suspicious Merchant, Round Figure, Anomaly)
        cursor.execute('''
            INSERT INTO expenses (employee_id, trip_id, expense_date, category, merchant, amount, currency, payment_method, business_purpose, receipt_filename, notes, status, manager_decision, admin_decision, reimbursement_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'EMP-1001',
            None,
            '2026-09-25',
            'Food',
            'Luxury Casino & Spa Resort Exclusive',
            45000.00,
            'INR',
            'Cash',
            'Informal weekend client entertainment and dinner',
            'receipt_suspicious_club.txt',
            'Team dinner after launch',
            'Pending',
            'Pending',
            'Suspicious',
            'Pending'
        ))
        exp_3_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO fraud_results (expense_id, risk_score, risk_level, fraud_reasons, ocr_summary, anomaly_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            exp_3_id,
            88,
            'HIGH RISK',
            json.dumps([
                "Amount ₹45,000.00 strictly exceeds corporate ceiling limit (₹6,000.00) for category 'Food'.",
                "AI Isolation Forest algorithm identified statistical amount anomaly (Deviation score: -2.85).",
                "Merchant 'Luxury Casino & Spa Resort Exclusive' appears to be associated with non-reimbursable entertainment/personal expenses.",
                "Weekend expense on Friday/Saturday without adequate business justification notes.",
                "Round figure amount (₹45,000.00) with cash payment method."
            ]),
            "Warning: Merchant name indicates non-business expense (casino, spa resort exclusive).",
            -0.85
        ))

        conn.commit()

    conn.close()


# Authentication Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this portal page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please sign in to access this portal page.", "warning")
                return redirect(url_for('login'))
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash(f"Unauthorized. Access restricted to {', '.join(allowed_roles)}.", "error")
                if user_role == 'Employee':
                    return redirect(url_for('employee_dashboard'))
                elif user_role == 'Manager':
                    return redirect(url_for('manager_dashboard'))
                elif user_role == 'Admin':
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --------------------------------------------------------------------------
# PUBLIC & AUTHENTICATION ROUTES
# --------------------------------------------------------------------------

@app.route('/')
def index():
    """Landing Home Page"""
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Sign In Route supporting Employee, Manager, and Admin accounts."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template('login.html')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['employee_id'] = user['employee_id']
            session['user_name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']
            session['department'] = user['department']

            flash(f"Welcome back, {user['name']}! Login successful.", "success")

            # Route by role
            if user['role'] == 'Employee':
                return redirect(url_for('employee_dashboard'))
            elif user['role'] == 'Manager':
                return redirect(url_for('manager_dashboard'))
            elif user['role'] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password. Please verify credentials.", "error")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Employee Self-Registration Route"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        employee_id = request.form.get('employee_id', '').strip().upper()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        designation = request.form.get('designation', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        if not all([name, employee_id, email, phone, department, designation, password, confirm_password]):
            flash("All fields are mandatory for corporate registration.", "error")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "error")
            return render_template('register.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template('register.html')

        conn = get_db()
        cursor = conn.cursor()

        # Check existing employee ID or email
        cursor.execute("SELECT id FROM users WHERE employee_id = ? OR LOWER(email) = ?", (employee_id, email))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            flash("An account with this Employee ID or Email already exists.", "error")
            return render_template('register.html')

        hashed_pw = generate_password_hash(password)
        try:
            cursor.execute('''
                INSERT INTO users (name, employee_id, email, phone, department, designation, password, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Employee')
            ''', (name, employee_id, email, phone, department, designation, hashed_pw))
            conn.commit()
            conn.close()

            flash("Registration successful! Please sign in with your corporate email.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            conn.close()
            flash(f"Database error during registration: {str(e)}", "error")
            return render_template('register.html')

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Clear session and log out."""
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for('login'))


# --------------------------------------------------------------------------
# EMPLOYEE ROUTES
# --------------------------------------------------------------------------

@app.route('/employee/dashboard')
@login_required
@role_required(['Employee'])
def employee_dashboard():
    """Employee Portal Dashboard"""
    emp_id = session.get('employee_id')
    conn = get_db()
    cursor = conn.cursor()

    # User Profile Info
    cursor.execute("SELECT * FROM users WHERE employee_id = ?", (emp_id,))
    user = cursor.fetchone()

    # Total Expenses & Stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total_count,
            COALESCE(SUM(amount), 0) as total_amount,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) as approved_count,
            SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) as rejected_count
        FROM expenses WHERE employee_id = ?
    """, (emp_id,))
    stats_row = cursor.fetchone()

    # Total Reimbursed Amount
    cursor.execute("""
        SELECT COALESCE(SUM(reimbursement_amount), 0) FROM reimbursements WHERE employee_id = ?
    """, (emp_id,))
    reimbursed_total = cursor.fetchone()[0]

    # High Risk Fraud Count
    cursor.execute("""
        SELECT COUNT(*) FROM expenses e
        JOIN fraud_results f ON e.id = f.expense_id
        WHERE e.employee_id = ? AND f.risk_level = 'HIGH RISK'
    """, (emp_id,))
    high_risk_count = cursor.fetchone()[0]

    stats = {
        'total_count': stats_row['total_count'] or 0,
        'total_amount': stats_row['total_amount'] or 0.0,
        'pending_count': stats_row['pending_count'] or 0,
        'approved_count': stats_row['approved_count'] or 0,
        'rejected_count': stats_row['rejected_count'] or 0,
        'reimbursed_amount': reimbursed_total or 0.0,
        'high_risk_count': high_risk_count or 0
    }

    # Recent Expenses with Fraud Results
    cursor.execute("""
        SELECT e.*, f.risk_score, f.risk_level
        FROM expenses e
        LEFT JOIN fraud_results f ON e.id = f.expense_id
        WHERE e.employee_id = ?
        ORDER BY e.id DESC LIMIT 6
    """, (emp_id,))
    recent_expenses = cursor.fetchall()

    # Travel Requests
    cursor.execute("""
        SELECT * FROM travel_requests
        WHERE employee_id = ?
        ORDER BY id DESC LIMIT 5
    """, (emp_id,))
    travel_requests = cursor.fetchall()

    conn.close()
    return render_template(
        'employee_dashboard.html',
        user=user,
        stats=stats,
        recent_expenses=recent_expenses,
        travel_requests=travel_requests
    )


@app.route('/employee/travel_request', methods=['GET', 'POST'])
@login_required
@role_required(['Employee'])
def travel_request():
    """Submit Corporate Travel Pre-Approval Request"""
    emp_id = session.get('employee_id')

    if request.method == 'POST':
        purpose = request.form.get('purpose', '').strip()
        source = request.form.get('source', '').strip()
        destination = request.form.get('destination', '').strip()
        travel_type = request.form.get('travel_type', 'Domestic')
        from_date = request.form.get('from_date', '')
        to_date = request.form.get('to_date', '')
        travel_mode = request.form.get('travel_mode', 'Flight')
        estimated_cost = float(request.form.get('estimated_cost', 0.0))
        accommodation = request.form.get('accommodation', 'No')
        advance_required = float(request.form.get('advance_required', 0.0))
        description = request.form.get('description', '').strip()

        if not all([purpose, source, destination, from_date, to_date, travel_mode]) or estimated_cost <= 0:
            flash("Please fill in all mandatory travel itinerary details and valid estimated cost.", "error")
            return render_template('travel_request.html')

        if from_date > to_date:
            flash("Departure date cannot be later than return date.", "error")
            return render_template('travel_request.html')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO travel_requests (employee_id, purpose, source, destination, travel_type, from_date, to_date, travel_mode, estimated_cost, accommodation, advance_required, description, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
        ''', (emp_id, purpose, source, destination, travel_type, from_date, to_date, travel_mode, estimated_cost, accommodation, advance_required, description))
        conn.commit()
        conn.close()

        flash("Travel request submitted successfully! Pending manager pre-approval.", "success")
        return redirect(url_for('employee_dashboard'))

    return render_template('travel_request.html')


@app.route('/employee/expense_form', methods=['GET', 'POST'])
@login_required
@role_required(['Employee'])
def expense_form():
    """Submit Expense Claim with AI Fraud Scoring"""
    emp_id = session.get('employee_id')
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        trip_id = request.form.get('trip_id')
        trip_id = int(trip_id) if trip_id and trip_id.isdigit() else None
        expense_date = request.form.get('expense_date', '').strip()
        category = request.form.get('category', 'Other')
        merchant = request.form.get('merchant', '').strip()
        amount_raw = request.form.get('amount', 0.0)
        currency = request.form.get('currency', 'INR')
        payment_method = request.form.get('payment_method', 'UPI')
        business_purpose = request.form.get('business_purpose', '').strip()
        notes = request.form.get('notes', '').strip()

        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Please enter a valid positive expense claim amount.", "error")
            conn.close()
            return redirect(url_for('expense_form'))

        if not all([expense_date, category, merchant, business_purpose]):
            flash("Please fill in all mandatory expense fields.", "error")
            conn.close()
            return redirect(url_for('expense_form'))

        # Handle Receipt File Upload
        receipt_filename = None
        if 'receipt' in request.files:
            file = request.files['receipt']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    safe_name = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    receipt_filename = f"{emp_id}_{timestamp}_{safe_name}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], receipt_filename))
                else:
                    flash("Invalid file format. Allowed formats: PNG, JPG, JPEG, PDF, TXT, WEBP.", "error")
                    conn.close()
                    return redirect(url_for('expense_form'))

        # Insert Expense into Database
        cursor.execute('''
            INSERT INTO expenses (employee_id, trip_id, expense_date, category, merchant, amount, currency, payment_method, business_purpose, receipt_filename, notes, status, manager_decision, admin_decision, reimbursement_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', 'Pending', 'Pending', 'Pending')
        ''', (emp_id, trip_id, expense_date, category, merchant, amount, currency, payment_method, business_purpose, receipt_filename, notes))
        
        expense_id = cursor.lastrowid

        # Fetch Linked Trip details if applicable
        linked_trip = None
        if trip_id:
            cursor.execute("SELECT * FROM travel_requests WHERE id = ?", (trip_id,))
            linked_trip_row = cursor.fetchone()
            if linked_trip_row:
                linked_trip = dict(linked_trip_row)

        # Fetch all historical expenses for anomaly and duplicate analysis
        cursor.execute("SELECT * FROM expenses")
        all_expenses_db = [dict(row) for row in cursor.fetchall()]

        # Prepare expense dict for AI evaluation
        current_expense_data = {
            'id': expense_id,
            'employee_id': emp_id,
            'category': category,
            'merchant': merchant,
            'amount': amount,
            'expense_date': expense_date,
            'receipt_filename': receipt_filename,
            'notes': notes,
            'business_purpose': business_purpose
        }

        # Run AI Fraud Detection Engine
        ai_assessment = evaluate_expense_fraud(
            expense_data=current_expense_data,
            linked_trip=linked_trip,
            all_expenses_db=all_expenses_db,
            uploads_folder=app.config['UPLOAD_FOLDER']
        )

        # Store Fraud Assessment Results
        cursor.execute('''
            INSERT INTO fraud_results (expense_id, risk_score, risk_level, fraud_reasons, ocr_summary, anomaly_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            expense_id,
            ai_assessment['risk_score'],
            ai_assessment['risk_level'],
            json.dumps(ai_assessment['fraud_reasons']),
            ai_assessment['ocr_summary'],
            ai_assessment['anomaly_score']
        ))

        conn.commit()
        conn.close()

        flash(f"Expense claim #EXP-{expense_id} submitted! AI Risk Score: {ai_assessment['risk_score']}% ({ai_assessment['risk_level']}).", "success")
        return redirect(url_for('expense_details', expense_id=expense_id))

    # GET: Load employee's approved/active trips
    cursor.execute("SELECT * FROM travel_requests WHERE employee_id = ? ORDER BY id DESC", (emp_id,))
    user_trips = cursor.fetchall()
    conn.close()

    return render_template('expense_form.html', user_trips=user_trips)


@app.route('/employee/expense_history')
@login_required
@role_required(['Employee'])
def expense_history():
    """View Complete Personal Expense History"""
    emp_id = session.get('employee_id')
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.*, f.risk_score, f.risk_level
        FROM expenses e
        LEFT JOIN fraud_results f ON e.id = f.expense_id
        WHERE e.employee_id = ?
        ORDER BY e.id DESC
    """, (emp_id,))
    expenses = cursor.fetchall()
    conn.close()

    return render_template('expense_history.html', expenses=expenses)


@app.route('/expense/details/<int:expense_id>')
@login_required
def expense_details(expense_id):
    """View Detailed Audit Sheet for Any Expense Claim"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    expense = cursor.fetchone()

    if not expense:
        conn.close()
        flash("Expense claim not found.", "error")
        return redirect(url_for('index'))

    # Permission check: Employee can only view their own claims
    if session.get('role') == 'Employee' and expense['employee_id'] != session.get('employee_id'):
        conn.close()
        flash("Unauthorized access to this expense claim.", "error")
        return redirect(url_for('employee_dashboard'))

    # Fetch Employee details
    cursor.execute("SELECT * FROM users WHERE employee_id = ?", (expense['employee_id'],))
    employee = cursor.fetchone()

    # Fetch Fraud Detection Analysis
    cursor.execute("SELECT * FROM fraud_results WHERE expense_id = ?", (expense_id,))
    fraud = cursor.fetchone()

    fraud_reasons_list = []
    if fraud and fraud['fraud_reasons']:
        try:
            fraud_reasons_list = json.loads(fraud['fraud_reasons'])
        except Exception:
            fraud_reasons_list = [fraud['fraud_reasons']]

    # Fetch Linked Trip details
    trip = None
    if expense['trip_id']:
        cursor.execute("SELECT * FROM travel_requests WHERE id = ?", (expense['trip_id'],))
        trip = cursor.fetchone()

    # Fetch Reimbursement info if processed
    cursor.execute("SELECT * FROM reimbursements WHERE expense_id = ?", (expense_id,))
    reimbursement_data = cursor.fetchone()

    conn.close()
    return render_template(
        'expense_details.html',
        expense=expense,
        employee=employee,
        fraud=fraud,
        fraud_reasons_list=fraud_reasons_list,
        trip=trip,
        reimbursement_data=reimbursement_data
    )


# --------------------------------------------------------------------------
# MANAGER ROUTES
# --------------------------------------------------------------------------

@app.route('/manager/dashboard')
@login_required
@role_required(['Manager'])
def manager_dashboard():
    """Manager Team Approval Dashboard"""
    conn = get_db()
    cursor = conn.cursor()

    # Manager Stats
    cursor.execute("SELECT COUNT(*) FROM expenses WHERE status = 'Pending'")
    pending_expenses_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM travel_requests WHERE status = 'Pending'")
    pending_travel_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM expenses e
        JOIN fraud_results f ON e.id = f.expense_id
        WHERE f.risk_level = 'HIGH RISK' AND e.status = 'Pending'
    """)
    high_risk_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM expenses")
    total_expenses_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM travel_requests")
    total_travel_count = cursor.fetchone()[0]

    stats = {
        'pending_expenses': pending_expenses_count,
        'pending_travel': pending_travel_count,
        'high_risk_expenses': high_risk_count,
        'total_expenses': total_expenses_count,
        'total_travel': total_travel_count
    }

    # All Expenses with AI Score & Employee Info
    cursor.execute("""
        SELECT e.*, u.name as employee_name, f.risk_score, f.risk_level
        FROM expenses e
        LEFT JOIN users u ON e.employee_id = u.employee_id
        LEFT JOIN fraud_results f ON e.id = f.expense_id
        ORDER BY CASE WHEN e.status = 'Pending' THEN 0 ELSE 1 END, e.id DESC
    """)
    all_expenses = cursor.fetchall()

    # High Risk Claims List
    cursor.execute("""
        SELECT e.*, u.name as employee_name, f.risk_score, f.risk_level, f.fraud_reasons
        FROM expenses e
        LEFT JOIN users u ON e.employee_id = u.employee_id
        LEFT JOIN fraud_results f ON e.id = f.expense_id
        WHERE f.risk_level = 'HIGH RISK'
        ORDER BY e.id DESC LIMIT 5
    """)
    high_risk_raw = cursor.fetchall()
    high_risk_claims = []
    for row in high_risk_raw:
        item = dict(row)
        try:
            reasons = json.loads(item['fraud_reasons'])
            item['top_reason'] = reasons[0] if reasons else 'High anomaly flag'
        except Exception:
            item['top_reason'] = 'Anomaly detected'
        high_risk_claims.append(item)

    # Travel Pre-Approval Requests
    cursor.execute("""
        SELECT t.*, u.name as employee_name
        FROM travel_requests t
        LEFT JOIN users u ON t.employee_id = u.employee_id
        ORDER BY CASE WHEN t.status = 'Pending' THEN 0 ELSE 1 END, t.id DESC
    """)
    travel_requests = cursor.fetchall()

    conn.close()
    return render_template(
        'manager_dashboard.html',
        stats=stats,
        all_expenses=all_expenses,
        high_risk_claims=high_risk_claims,
        travel_requests=travel_requests
    )


@app.route('/manager/action/<int:expense_id>', methods=['POST'])
@login_required
@role_required(['Manager'])
def manager_action(expense_id):
    """Manager Approve / Reject / Clarification on Expense Claims"""
    action = request.form.get('action')
    if action not in ['Approve', 'Reject', 'Request Clarification']:
        flash("Invalid action command.", "error")
        return redirect(url_for('manager_dashboard'))

    new_status = 'Approved' if action == 'Approve' else ('Rejected' if action == 'Reject' else 'Needs Clarification')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE expenses
        SET status = ?, manager_decision = ?
        WHERE id = ?
    """, (new_status, action, expense_id))
    conn.commit()
    conn.close()

    flash(f"Expense claim #EXP-{expense_id} status updated to '{new_status}'.", "success")
    return redirect(url_for('manager_dashboard'))


@app.route('/manager/trip_action/<int:trip_id>', methods=['POST'])
@login_required
@role_required(['Manager'])
def manager_trip_action(trip_id):
    """Manager Approve / Reject on Travel Pre-Approval Request"""
    action = request.form.get('action')
    status_map = {'Approve': 'Approved', 'Reject': 'Rejected'}
    new_status = status_map.get(action, 'Pending')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE travel_requests
        SET status = ?, manager_comment = ?
        WHERE id = ?
    """, (new_status, f"Decision by {session.get('user_name')}", trip_id))
    conn.commit()
    conn.close()

    flash(f"Travel request #TRIP-{trip_id} has been marked as '{new_status}'.", "success")
    return redirect(url_for('manager_dashboard'))


# --------------------------------------------------------------------------
# ADMIN & FINANCE ROUTES
# --------------------------------------------------------------------------

@app.route('/admin/dashboard')
@login_required
@role_required(['Admin'])
def admin_dashboard():
    """Admin & Finance Analytics Dashboard"""
    conn = get_db()
    cursor = conn.cursor()

    # Metrics
    cursor.execute("SELECT COUNT(*) FROM users")
    total_employees = cursor.fetchone()[0]

    cursor.execute("""
        SELECT 
            COUNT(*) as total_count,
            COALESCE(SUM(amount), 0) as total_amount,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) as approved_count,
            SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) as rejected_count
        FROM expenses
    """)
    expense_stats = cursor.fetchone()

    cursor.execute("""
        SELECT 
            SUM(CASE WHEN risk_level = 'LOW RISK' THEN 1 ELSE 0 END) as low_count,
            SUM(CASE WHEN risk_level = 'MEDIUM RISK' THEN 1 ELSE 0 END) as med_count,
            SUM(CASE WHEN risk_level = 'HIGH RISK' THEN 1 ELSE 0 END) as high_count
        FROM fraud_results
    """)
    risk_stats = cursor.fetchone()

    cursor.execute("SELECT COALESCE(SUM(reimbursement_amount), 0) FROM reimbursements")
    total_reimbursed = cursor.fetchone()[0]

    stats = {
        'total_employees': total_employees,
        'total_expenses_count': expense_stats['total_count'] or 0,
        'total_expenses_amount': expense_stats['total_amount'] or 0.0,
        'pending_count': expense_stats['pending_count'] or 0,
        'approved_count': expense_stats['approved_count'] or 0,
        'rejected_count': expense_stats['rejected_count'] or 0,
        'low_risk_count': risk_stats['low_count'] or 0,
        'medium_risk_count': risk_stats['med_count'] or 0,
        'high_risk_count': risk_stats['high_count'] or 0,
        'total_reimbursed_amount': total_reimbursed or 0.0
    }

    # Chart 1: Spend by Category
    cursor.execute("SELECT category, SUM(amount) as cat_total FROM expenses GROUP BY category")
    cat_rows = cursor.fetchall()
    chart_category_labels = [r['category'] for r in cat_rows] if cat_rows else ['Food', 'Taxi', 'Hotel', 'Flight']
    chart_category_data = [float(r['cat_total']) for r in cat_rows] if cat_rows else [0, 0, 0, 0]

    # All Expenses
    cursor.execute("""
        SELECT e.*, u.name as employee_name, f.risk_score, f.risk_level
        FROM expenses e
        LEFT JOIN users u ON e.employee_id = u.employee_id
        LEFT JOIN fraud_results f ON e.id = f.expense_id
        ORDER BY e.id DESC
    """)
    all_expenses = cursor.fetchall()

    # User Directory
    cursor.execute("SELECT * FROM users ORDER BY role, id ASC")
    users = cursor.fetchall()

    conn.close()
    return render_template(
        'admin_dashboard.html',
        stats=stats,
        chart_category_labels=chart_category_labels,
        chart_category_data=chart_category_data,
        all_expenses=all_expenses,
        users=users
    )


@app.route('/admin/fraud_review')
@login_required
@role_required(['Admin'])
def fraud_review():
    """Dedicated AI Fraud Review and Compliance Investigation Console"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.*, u.name as employee_name, u.department, f.risk_score, f.risk_level, f.fraud_reasons, f.ocr_summary
        FROM expenses e
        JOIN fraud_results f ON e.id = f.expense_id
        JOIN users u ON e.employee_id = u.employee_id
        WHERE f.risk_score >= 31
        ORDER BY f.risk_score DESC, e.id DESC
    """)
    raw_flagged = cursor.fetchall()
    flagged_expenses = []

    for row in raw_flagged:
        item = dict(row)
        try:
            item['reasons_list'] = json.loads(item['fraud_reasons'])
        except Exception:
            item['reasons_list'] = [item['fraud_reasons']]
        flagged_expenses.append(item)

    conn.close()
    return render_template('fraud_review.html', flagged_expenses=flagged_expenses)


@app.route('/admin/fraud_decision/<int:expense_id>', methods=['POST'])
@login_required
@role_required(['Admin'])
def admin_fraud_decision(expense_id):
    """Admin Mark as Genuine / Suspicious / Fraudulent / Needs Info"""
    decision = request.form.get('decision')
    if decision not in ['Genuine', 'Suspicious', 'Fraudulent', 'Needs Info']:
        flash("Invalid audit decision.", "error")
        return redirect(url_for('fraud_review'))

    conn = get_db()
    cursor = conn.cursor()
    
    # Update admin decision and status
    new_status = 'Rejected' if decision == 'Fraudulent' else ('Approved' if decision == 'Genuine' else 'Needs Clarification')
    cursor.execute("""
        UPDATE expenses
        SET admin_decision = ?, status = CASE WHEN ? = 'Fraudulent' THEN 'Rejected' ELSE status END
        WHERE id = ?
    """, (decision, decision, expense_id))
    conn.commit()
    conn.close()

    flash(f"Claim #EXP-{expense_id} official audit verdict set to: '{decision}'.", "success")
    return redirect(url_for('fraud_review'))


@app.route('/admin/reimbursement')
@login_required
@role_required(['Admin'])
def reimbursement():
    """Finance Reimbursement Disbursement Management"""
    selected_id = request.args.get('expense_id', type=int)
    conn = get_db()
    cursor = conn.cursor()

    # Approved Claims waiting for payout
    cursor.execute("""
        SELECT e.*, u.name as employee_name, f.risk_score, f.risk_level
        FROM expenses e
        JOIN users u ON e.employee_id = u.employee_id
        LEFT JOIN fraud_results f ON e.id = f.expense_id
        WHERE e.status = 'Approved' AND e.reimbursement_status != 'Reimbursed'
        ORDER BY e.id DESC
    """)
    approved_unpaid = cursor.fetchall()

    # Completed Reimbursements
    cursor.execute("""
        SELECT r.*, u.name as employee_name
        FROM reimbursements r
        JOIN users u ON r.employee_id = u.employee_id
        ORDER BY r.id DESC
    """)
    completed_reimbursements = cursor.fetchall()

    # Selected expense for instant payout form
    selected_expense = None
    if selected_id:
        cursor.execute("""
            SELECT e.*, u.name as employee_name
            FROM expenses e
            JOIN users u ON e.employee_id = u.employee_id
            WHERE e.id = ?
        """, (selected_id,))
        selected_expense = cursor.fetchone()

    conn.close()
    return render_template(
        'reimbursement.html',
        approved_unpaid=approved_unpaid,
        completed_reimbursements=completed_reimbursements,
        selected_expense=selected_expense,
        today_date=date.today().strftime('%Y-%m-%d')
    )


@app.route('/admin/process_reimbursement', methods=['POST'])
@login_required
@role_required(['Admin'])
def process_reimbursement():
    """Process settlement and disburse funds to employee"""
    expense_id = request.form.get('expense_id', type=int)
    employee_id = request.form.get('employee_id', '').strip()
    approved_amount = float(request.form.get('approved_amount', 0.0))
    reimbursement_amount = float(request.form.get('reimbursement_amount', 0.0))
    payment_method = request.form.get('payment_method', 'Direct Bank Transfer')
    payment_date = request.form.get('payment_date', date.today().strftime('%Y-%m-%d'))
    transaction_id = request.form.get('transaction_id', '').strip()
    comments = request.form.get('comments', '').strip()
    status = request.form.get('status', 'Reimbursed')

    if not all([expense_id, employee_id, transaction_id]) or reimbursement_amount <= 0:
        flash("Please provide all mandatory settlement details and valid transaction reference.", "error")
        return redirect(url_for('reimbursement'))

    conn = get_db()
    cursor = conn.cursor()

    # Insert Reimbursement Record
    cursor.execute('''
        INSERT INTO reimbursements (expense_id, employee_id, approved_amount, reimbursement_amount, payment_method, payment_date, transaction_id, comments, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (expense_id, employee_id, approved_amount, reimbursement_amount, payment_method, payment_date, transaction_id, comments, status))

    # Update Expense reimbursement status
    cursor.execute("""
        UPDATE expenses
        SET reimbursement_status = ?
        WHERE id = ?
    """, (status, expense_id))

    conn.commit()
    conn.close()

    flash(f"Reimbursement of ₹{reimbursement_amount:,.2f} for claim #EXP-{expense_id} processed successfully! TXN: {transaction_id}", "success")
    return redirect(url_for('reimbursement'))


# --------------------------------------------------------------------------
# FILE SERVING
# --------------------------------------------------------------------------

@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    """Securely serve uploaded receipt files to authenticated users."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# --------------------------------------------------------------------------
# INITIALIZATION & APP ENTRYPOINT
# --------------------------------------------------------------------------

if __name__ == '__main__':
    # Initialize SQLite Database with schema and sample demo records
    init_db()
    print("=" * 70)
    print(" AI Powered Smart Travel Expense Fraud Identifier & Reimbursement Portal")
    print(" Server running on: http://127.0.0.1:5000")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5000, debug=True)
