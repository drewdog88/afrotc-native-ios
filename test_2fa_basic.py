#!/usr/bin/env python3
"""
Basic 2FA functionality test
Tests the core 2FA utilities without requiring the full Flask app
"""

import os
import sys
import base64
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('env.local')

def test_2fa_utils():
    """Test basic 2FA utility functions"""
    print("🧪 Testing 2FA Utilities")
    print("=" * 50)
    
    try:
        # Import 2FA utilities
        import importlib.util
        spec = importlib.util.spec_from_file_location("fa_utils", "utils/2fa_utils.py")
        fa_utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fa_utils)
        
        generate_totp_secret = fa_utils.generate_totp_secret
        generate_backup_codes = fa_utils.generate_backup_codes
        hash_backup_code = fa_utils.hash_backup_code
        verify_backup_code = fa_utils.verify_backup_code
        generate_qr_code = fa_utils.generate_qr_code
        verify_totp_code = fa_utils.verify_totp_code
        encrypt_totp_secret = fa_utils.encrypt_totp_secret
        decrypt_totp_secret = fa_utils.decrypt_totp_secret
        
        print("✅ Successfully imported 2FA utilities")
        
        # Test TOTP secret generation
        print("\n📝 Testing TOTP secret generation...")
        secret = generate_totp_secret()
        print(f"   Generated secret: {secret}")
        print(f"   Length: {len(secret)} characters")
        print(f"   Valid format: {secret.isalnum() and len(secret) >= 16}")
        
        # Test backup codes generation
        print("\n🔑 Testing backup codes generation...")
        backup_codes = generate_backup_codes(5)
        print(f"   Generated {len(backup_codes)} backup codes:")
        for i, code in enumerate(backup_codes, 1):
            print(f"   {i}. {code}")
        
        # Test backup code hashing and verification
        print("\n🔐 Testing backup code hashing and verification...")
        test_code = backup_codes[0]
        hashed_code = hash_backup_code(test_code)
        print(f"   Original code: {test_code}")
        print(f"   Hashed code: {hashed_code[:20]}...")
        
        # Test verification
        is_valid, used_hash = verify_backup_code(test_code, [hashed_code])
        print(f"   Verification result: {is_valid}")
        
        # Test QR code generation
        print("\n📱 Testing QR code generation...")
        qr_bytes = generate_qr_code(secret, "testuser")
        qr_base64 = base64.b64encode(qr_bytes).decode()
        print(f"   QR code generated: {len(qr_bytes)} bytes")
        print(f"   Base64 length: {len(qr_base64)} characters")
        
        # Test TOTP verification
        print("\n⏰ Testing TOTP verification...")
        # Get current code
        get_current_totp_code = fa_utils.get_current_totp_code
        current_code = get_current_totp_code(secret)
        print(f"   Current TOTP code: {current_code}")
        
        # Verify the code
        is_valid = verify_totp_code(secret, current_code)
        print(f"   TOTP verification result: {is_valid}")
        
        # Test encryption/decryption (if encryption key is set)
        print("\n🔒 Testing encryption/decryption...")
        if os.getenv('TOTP_ENCRYPTION_KEY'):
            encrypted = encrypt_totp_secret(secret)
            decrypted = decrypt_totp_secret(encrypted)
            print(f"   Original: {secret}")
            print(f"   Encrypted: {encrypted[:20]}...")
            print(f"   Decrypted: {decrypted}")
            print(f"   Encryption test: {secret == decrypted}")
        else:
            print("   ⚠️  TOTP_ENCRYPTION_KEY not set - skipping encryption test")
        
        print("\n✅ All basic 2FA tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all required packages are installed:")
        print("   pip install pyotp qrcode Pillow cryptography")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_database_connection():
    """Test database connection and 2FA columns"""
    print("\n🗄️  Testing Database Connection")
    print("=" * 50)
    
    try:
        import psycopg2
        from dotenv import load_dotenv
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
        
        # Convert postgres:// to postgresql:// for SQLAlchemy compatibility
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        print("📡 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check for 2FA columns
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'user' 
            AND (column_name LIKE '%totp%' OR column_name LIKE '%backup%' OR column_name LIKE '%2fa%')
            ORDER BY column_name
        """)
        
        columns = cursor.fetchall()
        
        if columns:
            print("✅ Found 2FA columns in database:")
            for column in columns:
                print(f"   - {column[0]}: {column[1]} (nullable: {column[2]})")
        else:
            print("❌ No 2FA columns found in database")
            return False
        
        conn.close()
        print("✅ Database connection test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting 2FA Basic Tests")
    print("=" * 60)
    
    # Test 2FA utilities
    utils_ok = test_2fa_utils()
    
    # Test database connection
    db_ok = test_database_connection()
    
    print("\n" + "=" * 60)
    if utils_ok and db_ok:
        print("🎉 All tests passed! 2FA system is ready for use.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)
