#!/usr/bin/env python3

from app_local import app, db, User, PotentialRecruit
from flask import session
import os

def test_dashboard():
    """Test the dashboard route to reproduce the error"""
    
    with app.test_client() as client:
        with app.app_context():
            # First, let's check if we can query the tables directly
            print("=== Testing direct table queries ===")
            try:
                user_count = User.query.count()
                print(f"User count: {user_count}")
                
                recruit_count = PotentialRecruit.query.count()
                print(f"PotentialRecruit count: {recruit_count}")
                
            except Exception as e:
                print(f"❌ Error in direct queries: {e}")
                return
            
            # Now let's test the dashboard route
            print("\n=== Testing dashboard route ===")
            
            # First, we need to login to get a session
            print("1. Attempting login...")
            login_response = client.post('/login', data={
                'username': 'admin',
                'password': 'admin123'
            }, follow_redirects=True)
            
            print(f"Login status code: {login_response.status_code}")
            
            if login_response.status_code == 200:
                print("✅ Login successful")
                
                # Now try to access dashboard
                print("2. Attempting to access dashboard...")
                dashboard_response = client.get('/dashboard')
                
                print(f"Dashboard status code: {dashboard_response.status_code}")
                
                if dashboard_response.status_code == 200:
                    print("✅ Dashboard access successful")
                else:
                    print(f"❌ Dashboard failed with status: {dashboard_response.status_code}")
                    print(f"Response data: {dashboard_response.data.decode()[:500]}...")
            else:
                print("❌ Login failed")
                print(f"Response data: {login_response.data.decode()[:500]}...")

if __name__ == "__main__":
    test_dashboard()

