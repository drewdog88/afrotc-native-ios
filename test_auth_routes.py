import os
import unittest
from datetime import datetime
from app_local import app, db, User
from werkzeug.security import generate_password_hash
from sqlalchemy import text

class TestAuthRoutes(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        self.client = app.test_client()
        
        # Create test database and tables
        with app.app_context():
            # Drop all tables with CASCADE
            db.session.execute(text('DROP SCHEMA public CASCADE'))
            db.session.execute(text('CREATE SCHEMA public'))
            db.session.commit()
            
            # Create all tables
            db.create_all()
            
            # Create test user
            test_user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('testpass123'),
                first_name='Test',
                last_name='User',
                role='admin',
                secret_question='What is your favorite color?',
                secret_answer_hash=generate_password_hash('blue'),
                password_changed_at=datetime.utcnow(),
                force_password_change=False
            )
            db.session.add(test_user)
            db.session.commit()
    
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            # Drop all tables with CASCADE
            db.session.execute(text('DROP SCHEMA public CASCADE'))
            db.session.execute(text('CREATE SCHEMA public'))
            db.session.commit()
    
    def test_login_page_loads(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
    
    def test_successful_login(self):
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)
    
    def test_failed_login(self):
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpass'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid username or password', response.data)
    
    def test_account_lockout(self):
        # Attempt login with wrong password multiple times
        for _ in range(5):  # Assuming 5 is the max attempts
            self.client.post('/login', data={
                'username': 'testuser',
                'password': 'wrongpass'
            })
        
        # Check if account is locked
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)
        self.assertIn(b'Account is locked', response.data)
    
    def test_logout(self):
        # First login
        self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Then logout
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
    
    def test_forgot_password(self):
        response = self.client.post('/forgot-password', data={
            'username': 'testuser'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'security question', response.data.lower())
    
    def test_reset_password_question(self):
        # First go through forgot password flow to set up session
        self.client.post('/forgot-password', data={'username': 'testuser'})
        
        # Then test the reset password question page
        response = self.client.post('/reset-password-question', data={
            'secret_answer': 'blue'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reset Password', response.data)
    
    def test_reset_password(self):
        # First go through forgot password flow
        self.client.post('/forgot-password', data={
            'username': 'testuser'
        })
        self.client.post('/reset-password-question', data={
            'secret_answer': 'blue'
        })
        
        # Then reset password
        response = self.client.post('/reset-password', data={
            'new_password': 'NewPass123!',
            'confirm_password': 'NewPass123!'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'successfully reset', response.data.lower())
        
        # Try logging in with new password
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'NewPass123!'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)

if __name__ == '__main__':
    unittest.main()
