#!/usr/bin/env python3

import unittest
from api.app import app, db, User
from datetime import date

class TestApiSmoke(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            # Ensure DB exists and default admin present
            db.create_all()
            if not User.query.filter_by(username='admin').first():
                u = User(
                    username='admin',
                    email='admin@afrotc695.com',
                    first_name='Admin',
                    last_name='User',
                    password_hash=User(password_hash='x').password_hash,  # placeholder
                    secret_question='q',
                    secret_answer_hash='x'
                )
                db.session.add(u)
                db.session.commit()

    def test_login_and_add_event(self):
        # Load login page
        r = self.client.get('/login')
        self.assertEqual(r.status_code, 200)

        # Set password in DB for admin
        from werkzeug.security import generate_password_hash
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            admin.password_hash = generate_password_hash('admin123')
            db.session.commit()

        # Login
        r = self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(r.status_code, 200)

        # Access calendar
        rc = self.client.get('/calendar')
        self.assertEqual(rc.status_code, 200)

        # Add event
        form_data = {
            'title': 'API Smoke Event',
            'description': 'Smoke test event',
            'event_date': '2024-03-15',
            'start_time': '10:00',
            'end_time': '',
            'location': 'Test Location',
            'university_id': '',
            'event_type': 'info_session',
            'notes': 'test'
        }
        re = self.client.post('/calendar/add', data=form_data, follow_redirects=True)
        self.assertEqual(re.status_code, 200)

if __name__ == '__main__':
    unittest.main()














