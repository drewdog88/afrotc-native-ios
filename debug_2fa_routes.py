#!/usr/bin/env python3
"""
Debug script to test 2FA routes
"""
import app_local
from werkzeug.security import generate_password_hash

# Create test app and client
app = app_local.app
client = app.test_client()

# Create a test user
with app.app_context():
    app_local.db.create_all()
    
    # Check if user exists
    user = app_local.User.query.filter_by(username='testuser').first()
    if not user:
        user = app_local.User(
            username='testuser',
            email='test@example.com',
            password_hash=generate_password_hash('password123'),
            first_name='Test',
            last_name='User',
            role='user',
            is_active=True,
            secret_question='What is your favorite color?',
            secret_answer_hash=generate_password_hash('blue')
        )
        app_local.db.session.add(user)
        app_local.db.session.commit()
        print(f"Created user with ID: {user.id}")
    else:
        print(f"Found existing user with ID: {user.id}")

# Test without session (should redirect to login)
print("\n=== Testing without session ===")
response = client.get('/setup-2fa')
print(f"Status: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print(f"Data: {response.data[:200]}")

# Test with session
print("\n=== Testing with session ===")
with client.session_transaction() as sess:
    sess['user_id'] = user.id
    sess['username'] = user.username
    sess['role'] = user.role

response = client.get('/setup-2fa')
print(f"Status: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print(f"Data: {response.data[:200]}")

# Clean up
with app.app_context():
    app_local.db.session.remove()
    app_local.db.drop_all()






