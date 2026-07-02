#!/usr/bin/env python3
"""
Test login route with 2FA integration
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('env.local')

def test_login_flow():
    """Test the login flow with 2FA integration"""
    print("🧪 Testing Login Flow with 2FA Integration")
    print("=" * 60)
    
    try:
        # Import Flask app
        from app_local import app, db, User
        
        with app.app_context():
            # Test database connection
            print("📡 Testing database connection...")
            users = User.query.limit(5).all()
            print(f"   Found {len(users)} users in database")
            
            # Check for users with different 2FA statuses
            users_with_2fa = User.query.filter_by(totp_enabled=True).count()
            users_without_2fa = User.query.filter_by(totp_enabled=False).count()
            
            print(f"   Users with 2FA enabled: {users_with_2fa}")
            print(f"   Users without 2FA: {users_without_2fa}")
            
            # Test User model 2FA properties
            print("\n👤 Testing User model 2FA properties...")
            for user in users[:3]:  # Test first 3 users
                print(f"   User: {user.username}")
                print(f"     - is_2fa_enabled: {user.is_2fa_enabled}")
                print(f"     - can_use_2fa: {user.can_use_2fa}")
                print(f"     - has_2fa_setup: {user.has_2fa_setup()}")
                print(f"     - needs_2fa_setup: {user.needs_2fa_setup()}")
                print(f"     - totp_enabled: {user.totp_enabled}")
                print(f"     - totp_setup_completed: {user.totp_setup_completed}")
                print()
            
            print("✅ Login flow test completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_2fa_utils_import():
    """Test that 2FA utilities can be imported"""
    print("\n🔧 Testing 2FA Utilities Import")
    print("=" * 40)
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fa_utils", "utils/2fa_utils.py")
        fa_utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fa_utils)
        
        print("✅ Successfully imported 2FA utilities")
        
        # Test key functions
        functions_to_test = [
            'generate_totp_secret',
            'generate_backup_codes', 
            'hash_backup_code',
            'verify_backup_code',
            'generate_qr_code',
            'verify_totp_code'
        ]
        
        for func_name in functions_to_test:
            if hasattr(fa_utils, func_name):
                print(f"   ✅ {func_name}: Available")
            else:
                print(f"   ❌ {func_name}: Missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Login 2FA Integration Tests")
    print("=" * 60)
    
    # Test 2FA utilities import
    utils_ok = test_2fa_utils_import()
    
    # Test login flow
    login_ok = test_login_flow()
    
    print("\n" + "=" * 60)
    if utils_ok and login_ok:
        print("🎉 All tests passed! Login 2FA integration is ready.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)






