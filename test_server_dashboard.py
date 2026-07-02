#!/usr/bin/env python3

import requests

def test_server_dashboard():
    """Test the actual running Flask server dashboard access"""
    
    session = requests.Session()
    base_url = "http://localhost:5000"
    
    print("=== Testing actual Flask server ===")
    
    # Step 1: Get the login page
    print("1. Getting login page...")
    login_page = session.get(f"{base_url}/login")
    print(f"Login page status: {login_page.status_code}")
    
    if login_page.status_code == 200:
        print("✅ Login page accessible")
        
        # Step 2: Submit login form
        print("2. Submitting login form...")
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=True)
        print(f"Login response status: {login_response.status_code}")
        print(f"Login response URL: {login_response.url}")
        
        if login_response.status_code == 200:
            print("✅ Login successful")
            
            # Step 3: Try to access dashboard
            print("3. Accessing dashboard...")
            dashboard_response = session.get(f"{base_url}/dashboard")
            print(f"Dashboard status: {dashboard_response.status_code}")
            
            if dashboard_response.status_code == 200:
                print("✅ Dashboard accessible!")
                
                # Check if we got the dashboard content
                if 'Dashboard' in dashboard_response.text:
                    print("✅ Dashboard content found")
                else:
                    print("⚠️  Dashboard content not found")
                    
            else:
                print(f"❌ Dashboard failed with status: {dashboard_response.status_code}")
                print(f"Response content: {dashboard_response.text[:500]}...")
        else:
            print(f"❌ Login failed with status: {login_response.status_code}")
            print(f"Response content: {login_response.text[:500]}...")
    else:
        print(f"❌ Login page failed with status: {login_page.status_code}")

if __name__ == "__main__":
    test_server_dashboard()
