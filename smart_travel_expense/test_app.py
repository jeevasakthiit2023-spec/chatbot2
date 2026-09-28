"""
Automated End-to-End Verification Test Script
Tests all routes, database operations, AI fraud scoring, and multi-role workflows.
"""

import os
import sys
import unittest
import io
import json

# Ensure app is importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, init_db, get_db

class SmartExpensePortalTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        init_db()

    def test_01_landing_page(self):
        """Test public landing home page"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AI Powered Smart Travel Expense', response.data)
        self.assertIn(b'Employee Registration', response.data)

    def test_02_employee_login_and_dashboard(self):
        """Test Employee login and dashboard access"""
        response = self.client.post('/login', data={
            'email': 'employee@example.com',
            'password': 'employee123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome back, Alex Rivera!', response.data)
        self.assertIn(b'Employee Portal Dashboard', response.data)

    def test_03_manager_login_and_dashboard(self):
        """Test Manager login and dashboard access"""
        response = self.client.post('/login', data={
            'email': 'manager@example.com',
            'password': 'manager123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Manager Approval Portal', response.data)
        self.assertIn(b'Team Expense Claims', response.data)

    def test_04_admin_login_and_analytics(self):
        """Test Admin login and analytics dashboard"""
        response = self.client.post('/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Enterprise Admin & Finance Portal', response.data)
        self.assertIn(b'Expense Spend by Category', response.data)

    def test_05_register_new_employee(self):
        """Test new employee registration"""
        response = self.client.post('/register', data={
            'name': 'Test User',
            'employee_id': 'EMP-TEST-99',
            'email': 'testuser99@example.com',
            'phone': '+91 9988776655',
            'department': 'Engineering',
            'designation': 'QA Engineer',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registration successful', response.data)

        # Verify login with new credentials
        login_resp = self.client.post('/login', data={
            'email': 'testuser99@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn(b'Welcome back, Test User!', login_resp.data)

    def test_06_travel_request_submission_and_manager_approval(self):
        """Test travel pre-approval submission and manager decision"""
        # 1. Login as Employee
        self.client.post('/login', data={'email': 'employee@example.com', 'password': 'employee123'})
        
        # 2. Submit travel request
        tr_resp = self.client.post('/employee/travel_request', data={
            'purpose': 'Tokyo Client Demo Summit',
            'source': 'Bengaluru',
            'destination': 'Tokyo',
            'travel_type': 'International',
            'from_date': '2026-11-01',
            'to_date': '2026-11-07',
            'travel_mode': 'Flight',
            'estimated_cost': 85000.00,
            'accommodation': 'Yes',
            'advance_required': 25000.00,
            'description': 'Keynote demo for APAC partner alliance.'
        }, follow_redirects=True)
        self.assertEqual(tr_resp.status_code, 200)
        self.assertIn(b'Travel request submitted successfully', tr_resp.data)

        # 3. Login as Manager to approve
        self.client.get('/logout')
        self.client.post('/login', data={'email': 'manager@example.com', 'password': 'manager123'})
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM travel_requests WHERE purpose LIKE '%Tokyo%' ORDER BY id DESC LIMIT 1")
        trip_id = cursor.fetchone()[0]
        conn.close()

        mgr_resp = self.client.post(f'/manager/trip_action/{trip_id}', data={'action': 'Approve'}, follow_redirects=True)
        self.assertEqual(mgr_resp.status_code, 200)
        self.assertIn(b'Approved', mgr_resp.data)

    def test_07_clean_expense_submission_ai_scoring(self):
        """Test clean expense submission with low AI risk score"""
        self.client.post('/login', data={'email': 'employee@example.com', 'password': 'employee123'})

        receipt_data = (io.BytesIO(b"STARBUCKS COFFEE\nDate: 2026-09-20\nTotal: INR 450.00"), 'starbucks_receipt.txt')

        resp = self.client.post('/employee/expense_form', data={
            'category': 'Food',
            'merchant': 'Starbucks Coffee',
            'amount': '450.00',
            'currency': 'INR',
            'payment_method': 'UPI',
            'expense_date': '2026-09-20',
            'business_purpose': 'Client working breakfast meeting discussing sprint goals',
            'notes': 'Itemized coffee and sandwich',
            'receipt': receipt_data
        }, content_type='multipart/form-data', follow_redirects=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'LOW RISK', resp.data)

    def test_08_fraudulent_high_risk_expense_ai_detection(self):
        """Test expense with inflated amount and prohibited vendor (High Risk)"""
        self.client.post('/login', data={'email': 'employee@example.com', 'password': 'employee123'})

        resp = self.client.post('/employee/expense_form', data={
            'category': 'Food',
            'merchant': 'Grand VIP Casino Lounge',
            'amount': '55000.00',
            'currency': 'INR',
            'payment_method': 'Cash',
            'expense_date': '2026-09-21',
            'business_purpose': 'Client team entertainment',
            'notes': 'No itemized receipt'
        }, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'HIGH RISK', resp.data)
        self.assertIn(b'corporate ceiling limit', resp.data)

    def test_09_admin_fraud_review_and_decision(self):
        """Test Admin reviewing flagged claims and submitting a verdict"""
        self.client.post('/login', data={'email': 'admin@example.com', 'password': 'admin123'})

        resp = self.client.get('/admin/fraud_review')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'AI Fraud Investigation & Audit Console', resp.data)

        # Execute verdict on expense #3
        decision_resp = self.client.post('/admin/fraud_decision/3', data={'decision': 'Suspicious'}, follow_redirects=True)
        self.assertEqual(decision_resp.status_code, 200)
        self.assertIn(b'audit verdict set to', decision_resp.data)

    def test_10_finance_reimbursement_disbursement(self):
        """Test Finance processing reimbursement settlement"""
        self.client.post('/login', data={'email': 'admin@example.com', 'password': 'admin123'})

        reimb_page = self.client.get('/admin/reimbursement?expense_id=2')
        self.assertEqual(reimb_page.status_code, 200)
        self.assertIn(b'Process Settlement for Claim #EXP-2', reimb_page.data)

        process_resp = self.client.post('/admin/process_reimbursement', data={
            'expense_id': 2,
            'employee_id': 'EMP-1001',
            'approved_amount': 18500.00,
            'reimbursement_amount': 18500.00,
            'payment_method': 'UPI Direct Payout',
            'payment_date': '2026-09-26',
            'transaction_id': 'TXN-BANK-88219401',
            'comments': 'Paid in full via corporate netbanking channel.',
            'status': 'Reimbursed'
        }, follow_redirects=True)

        self.assertEqual(process_resp.status_code, 200)
        self.assertIn(b'processed successfully', process_resp.data)

if __name__ == '__main__':
    unittest.main()
