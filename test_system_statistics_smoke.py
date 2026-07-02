#!/usr/bin/env python3
"""
Smoke test for System Statistics functionality
Tests the actual route in the running application
"""

import requests
import time
import sys
import os

def test_system_statistics_smoke():
    """Smoke test for system statistics route"""
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 Starting System Statistics Smoke Test...")
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Server is running (Status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ Server is not running: {e}")
        return False
    
    # Test 2: Try to access system statistics without login (should redirect)
    try:
        response = requests.get(f"{base_url}/admin/system-statistics", timeout=5, allow_redirects=False)
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
        login_response = session.post(f"{base_url}/login", data=login_data, timeout=5)
        
        if login_response.status_code == 200 or login_response.status_code == 302:
            print("✅ Admin login successful")
            
            # Now try to access system statistics
            stats_response = session.get(f"{base_url}/admin/system-statistics", timeout=10)
            
            if stats_response.status_code == 200:
                print("✅ System statistics page loads successfully")
                
                # Check if the page contains expected content
                content = stats_response.text
                if "System Statistics" in content:
                    print("✅ System Statistics title found on page")
                else:
                    print("⚠️  System Statistics title not found on page")
                
                if "Database Size" in content or "Total Records" in content:
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

def test_helper_functions():
    """Test helper functions directly"""
    print("\n🔧 Testing Helper Functions...")
    
    try:
        from api.app import app, get_database_size, get_record_counts, get_system_performance, get_user_activity_stats, get_recruitment_stats
        
        with app.app_context():
            # Test database size
            db_size = get_database_size()
            print(f"✅ Database size function works: {db_size['total_size_mb']:.2f} MB")
            
            # Test record counts
            record_counts = get_record_counts()
            total_records = sum(record_counts.values())
            print(f"✅ Record counts function works: {total_records} total records")
            
            # Test system performance
            system_perf = get_system_performance()
            print(f"✅ System performance function works: CPU {system_perf['cpu_percent']}%")
            
            # Test user activity stats
            user_stats = get_user_activity_stats()
            print(f"✅ User activity stats function works: {user_stats['total_users']} users")
            
            # Test recruitment stats
            recruit_stats = get_recruitment_stats()
            print(f"✅ Recruitment stats function works: {recruit_stats['recent_recruits']} recent recruits")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing helper functions: {e}")
        return False

def check_route_registration():
    """Check if the system statistics route is properly registered"""
    print("\n🔍 Checking Route Registration...")
    
    try:
        from api.app import app
        
        # Get all registered routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(rule.rule)
        
        if '/admin/system-statistics' in routes:
            print("✅ System statistics route is registered")
            return True
        else:
            print("❌ System statistics route is NOT registered")
            print("Available admin routes:")
            admin_routes = [r for r in routes if '/admin/' in r]
            for route in admin_routes:
                print(f"  - {route}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking route registration: {e}")
        return False

if __name__ == "__main__":
    print("🚀 AFROTC 695 System Statistics Smoke Test")
    print("=" * 50)
    
    # Check route registration first
    route_registered = check_route_registration()
    
    # Test helper functions
    helper_success = test_helper_functions()
    
    # Test the web route
    route_success = test_system_statistics_smoke()
    
    print("\n" + "=" * 50)
    if route_registered and helper_success and route_success:
        print("🎉 ALL TESTS PASSED! System Statistics functionality is working correctly.")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED! Please check the implementation.")
        sys.exit(1)
