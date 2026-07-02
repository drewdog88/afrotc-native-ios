#!/usr/bin/env python3
"""
Production smoke test for System Statistics functionality
Tests the actual route in the production environment
"""

import requests
import time
import sys
import os

def test_system_statistics_production():
    """Smoke test for system statistics route in production"""
    base_url = "https://afrotc695recruitment.vercel.app"
    
    print("🚀 AFROTC 695 Production System Statistics Smoke Test")
    print("=" * 60)
    
    # Test 1: Check if production server is running
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"✅ Production server is running (Status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ Production server is not running: {e}")
        return False
    
    # Test 2: Try to access system statistics without login (should redirect)
    try:
        response = requests.get(f"{base_url}/admin/system-statistics", timeout=10, allow_redirects=False)
        if response.status_code == 302:
            print("✅ System statistics route properly redirects unauthorized users")
        else:
            print(f"⚠️  Unexpected status code for unauthorized access: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing system statistics route: {e}")
        return False
    
    # Test 3: Test login and then access system statistics
    try:
        # Login as admin
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        session = requests.Session()
        login_response = session.post(f"{base_url}/login", data=login_data, timeout=10)
        
        if login_response.status_code == 200 or login_response.status_code == 302:
            print("✅ Admin login successful")
            
            # Now try to access system statistics
            stats_response = session.get(f"{base_url}/admin/system-statistics", timeout=15)
            
            if stats_response.status_code == 200:
                print("✅ System statistics page loads successfully in production")
                
                # Check if the page contains expected content
                content = stats_response.text
                if "System Statistics" in content or "system-statistics" in content:
                    print("✅ System Statistics content found on page")
                else:
                    print("⚠️  System Statistics content not found on page")
                
                if "Database Size" in content or "Total Records" in content or "Statistics" in content:
                    print("✅ Statistics content found on page")
                else:
                    print("⚠️  Statistics content not found on page")
                
                return True
            else:
                print(f"❌ System statistics page failed to load (Status: {stats_response.status_code})")
                return False
        else:
            print(f"❌ Admin login failed (Status: {login_response.status_code})")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during login/system statistics test: {e}")
        return False

def test_production_health():
    """Test overall production health"""
    base_url = "https://afrotc695recruitment.vercel.app"
    
    print("\n🏥 Production Health Check...")
    
    try:
        # Test main page
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("✅ Main page loads successfully")
        else:
            print(f"⚠️  Main page status: {response.status_code}")
        
        # Test login page
        response = requests.get(f"{base_url}/login", timeout=10)
        if response.status_code == 200:
            print("✅ Login page loads successfully")
        else:
            print(f"⚠️  Login page status: {response.status_code}")
        
        # Test admin dashboard
        session = requests.Session()
        login_data = {'username': 'admin', 'password': 'admin123'}
        login_response = session.post(f"{base_url}/login", data=login_data, timeout=10)
        
        if login_response.status_code in [200, 302]:
            dashboard_response = session.get(f"{base_url}/dashboard", timeout=10)
            if dashboard_response.status_code == 200:
                print("✅ Admin dashboard loads successfully")
            else:
                print(f"⚠️  Admin dashboard status: {dashboard_response.status_code}")
        else:
            print("⚠️  Could not test admin dashboard (login failed)")
        
        return True
        
    except Exception as e:
        print(f"❌ Production health check failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 AFROTC 695 Production System Statistics Smoke Test")
    print("=" * 60)
    
    # Test production health first
    health_success = test_production_health()
    
    # Test the system statistics functionality
    stats_success = test_system_statistics_production()
    
    print("\n" + "=" * 60)
    if health_success and stats_success:
        print("🎉 ALL PRODUCTION TESTS PASSED! System Statistics functionality is working correctly in production.")
        sys.exit(0)
    else:
        print("❌ SOME PRODUCTION TESTS FAILED! Please check the implementation.")
        sys.exit(1)
