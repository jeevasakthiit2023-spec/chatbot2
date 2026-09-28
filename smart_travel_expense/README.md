# AI Powered Smart Travel Expense Fraud Identifier & Smart Reimbursement Portal

A complete, full-stack enterprise web application built for corporate travel governance, intelligent fraud identification, automated receipt auditing, and streamlined finance reimbursement.

---

## 🌟 Project Overview

Corporate travel expense fraud accounts for billions in lost corporate revenue annually through duplicate submissions, inflated hotel/food bills, altered receipts, and unauthorized claims. 

This portal provides an **end-to-end automated governance platform** that combines:
1. **Machine Learning Anomaly Detection (Scikit-Learn Isolation Forest)** to flag statistical expenditure outliers.
2. **Multi-Vector Heuristic Policy Audit** (10 vector rule matrix) checking duplicate expenses, hash-fingerprinted duplicate receipts, date misalignments, category thresholds, and suspicious vendors.
3. **Role-Based Workflow Automation** connecting **Employees**, **Managers**, and **Finance / Admin Auditors**.
4. **Smart Reimbursement Disbursement Pipeline** tracking payouts via UPI, Bank Transfer, and generating transaction audit logs.

> 🛡️ **AI Governance Notice:** *AI-generated risk assessment. Final decision requires human-in-the-loop admin/finance review.*

---

## 🛠️ Technology Stack

- **Frontend:** HTML5, Vanilla CSS3 (Custom responsive design system with dark sidebar, cards, and risk meters)
- **Backend:** Python Flask
- **Template Engine:** Jinja2
- **Database:** SQLite3 (`database.db`)
- **AI / Machine Learning:** Python, Scikit-Learn (`IsolationForest`), NumPy, Pandas
- **Receipt Analysis:** Digital receipt hash fingerprinting, heuristic keyword analysis, and mock OCR parsing
- **Security:** Werkzeug password hashing (PBKDF2/SHA256), session auth, role guards, secure filename upload checks
- **Visual Analytics:** Chart.js

---

## 📁 Project Structure

```
smart_travel_expense/
│
├── app.py                      # Main Flask application and REST endpoints
├── database.db                 # SQLite database (auto-generated on init)
├── requirements.txt            # Python package dependencies
├── README.md                   # Complete documentation
│
├── static/
│   └── style.css               # Professional custom CSS stylesheet
│
├── templates/
│   ├── base.html               # Master layout with sidebar, navigation & flash alerts
│   ├── index.html              # Landing page with feature showcases
│   ├── login.html              # Secure login with one-click demo auto-fill
│   ├── register.html           # Employee registration with form validation
│   ├── employee_dashboard.html # Employee KPI cards & recent claim overview
│   ├── travel_request.html     # Travel pre-approval itinerary form
│   ├── expense_form.html       # Expense submission with receipt upload
│   ├── expense_history.html    # Interactive search & historical audit records
│   ├── expense_details.html    # Deep-dive claim audit & AI reason breakdown
│   ├── manager_dashboard.html  # Manager team approval console
│   ├── admin_dashboard.html    # Executive analytics, charts & user directory
│   ├── fraud_review.html       # Compliance investigation & fraud triage
│   └── reimbursement.html      # Finance payout disbursement portal
│
├── uploads/                    # Secure folder for uploaded receipt vouchers
│
└── models/
    └── fraud_detection.py      # 10-vector AI Fraud & Anomaly Engine
```

---

## 🧠 AI Fraud Detection Logic & 10 Vectors

When an expense is submitted, `models/fraud_detection.py` analyzes the claim across 10 evaluation vectors:

1. **Duplicate Expense Vector:** Checks if an identical claim (same date, merchant, and amount) was already filed by the employee (+40 risk).
2. **Duplicate Receipt Fingerprinting:** Computes the MD5 file hash of uploaded vouchers to prevent reusing identical receipt images across claims (+45 risk).
3. **Category Benchmark Cap:** Compares claimed amounts against benchmark ceilings (e.g., Food > ₹6,000, Taxi > ₹8,000, Hotel > ₹25,000) (+20 to +35 risk).
4. **Machine Learning Anomaly Detection:** Applies Scikit-Learn `IsolationForest` to identify multi-dimensional outliers in historical category spending (+20 risk).
5. **Vendor & Category Consistency:** Scans merchant names for non-business keywords (e.g., casino, gaming, luxury boutique, spa) (+30 risk).
6. **Date Window Mismatch:** Verifies that the expense date aligns with approved travel itinerary dates and flags future claim dates (+30 to +35 risk).
7. **Missing Receipt Detection:** Flags claims over ₹500 that lack attached invoice vouchers (+25 risk).
8. **Rapid Succession Claims:** Detects 3 or more claims filed within 48 hours for the same category (+20 risk).
9. **Policy Violations:** Flags unjustified weekend expenditures or high round-figure claims lacking itemized bills (+15 risk).
10. **Repeated Vendor Spikes:** Detects abnormal frequency (>4 claims) to the same merchant within a 7-day window (+20 risk).

### Risk Classification:
- **0 – 30% : LOW RISK (Green)** — Clean audit profile, standard processing.
- **31 – 60% : MEDIUM RISK (Amber/Yellow)** — Warning flags detected; manager review advised.
- **61 – 100% : HIGH RISK (Red)** — Severe anomaly or policy violation; admin audit mandatory.

---

## 👥 User Roles & Access Control

| Role | Key Capabilities |
| :--- | :--- |
| **Employee** | Submit travel pre-approvals, file expense claims with receipt uploads, track AI risk ratings, and monitor reimbursement payouts. |
| **Manager** | Review department travel requests, approve/reject expense claims, inspect receipts, and review AI risk scores. |
| **Admin / Finance** | View analytics & Chart.js spend distributions, investigate flagged fraud in the AI Fraud Console, execute verdicts (Genuine / Suspicious / Fraudulent), and disburse fund reimbursements with transaction IDs. |

---

## ⚡ Quick Demo Credentials

The database is pre-seeded with ready-to-test accounts:

| Role | Email | Password | Pre-loaded Persona |
| :--- | :--- | :--- | :--- |
| **Employee** | `employee@example.com` | `employee123` | Alex Rivera (Lead Architect) |
| **Manager** | `manager@example.com` | `manager123` | Sarah Jenkins (Engineering Director) |
| **Admin / Finance** | `admin@example.com` | `admin123` | David Sterling (Chief Controller) |

*(One-click auto-fill buttons are provided on the login page for effortless testing)*

---

## 🚀 Installation & Running Instructions

### 1. Prerequisites
- Python 3.9+ (tested on Python 3.11)
- `pip` package manager

### 2. Navigate to the project directory
```bash
cd smart_travel_expense
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

### 5. Access the Web Application
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🗄️ Database Schema (SQLite)

- **`users`**: `id`, `name`, `employee_id`, `email`, `phone`, `department`, `designation`, `password` (hashed), `role`, `created_at`
- **`travel_requests`**: `id`, `employee_id`, `purpose`, `source`, `destination`, `travel_type`, `from_date`, `to_date`, `travel_mode`, `estimated_cost`, `accommodation`, `advance_required`, `description`, `status`, `manager_comment`, `created_at`
- **`expenses`**: `id`, `employee_id`, `trip_id`, `expense_date`, `category`, `merchant`, `amount`, `currency`, `payment_method`, `business_purpose`, `receipt_filename`, `notes`, `status`, `manager_decision`, `admin_decision`, `reimbursement_status`, `created_at`
- **`fraud_results`**: `id`, `expense_id`, `risk_score`, `risk_level`, `fraud_reasons`, `ocr_summary`, `anomaly_score`, `created_at`
- **`reimbursements`**: `id`, `expense_id`, `employee_id`, `approved_amount`, `reimbursement_amount`, `payment_method`, `payment_date`, `transaction_id`, `comments`, `status`, `created_at`

---

## 🔮 Future Enhancements

1. **Deep Neural Network OCR:** Integrate EasyOCR / Tesseract directly with bounding-box highlighting for line-item tax invoices.
2. **GPS Geolocation Verification:** Cross-reference merchant coordinates with mobile check-in locations.
3. **Automated Banking Webhooks:** Direct API integration with corporate banking rails (Stripe / RazorpayX) for instant disbursement.
4. **Corporate Credit Card Feeds:** Real-time transaction ingestion via Plaid or Open Banking APIs.
