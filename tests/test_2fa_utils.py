#!/usr/bin/env python3
"""
Unit Tests for 2FA Utility Functions
Tests all core 2FA functionality including encryption, TOTP, backup codes, and QR generation
"""

import unittest
import os
import tempfile
import json
import base64
from unittest.mock import patch, MagicMock
from io import BytesIO
import sys
import importlib.util
from dotenv import load_dotenv

# Load environment variables from env.local
load_dotenv('env.local')

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import 2FA utilities using dynamic import to avoid syntax errors
spec = importlib.util.spec_from_file_location("fa_utils", "utils/2fa_utils.py")
fa_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fa_utils)

class Test2FAUtils(unittest.TestCase):
    """Test suite for 2FA utility functions"""
    
    def setUp(self):
        """Set up test environment"""
        # Set up test encryption key
        self.test_key = "test_encryption_key_32_chars_long!"
        self.original_key = os.environ.get('TOTP_ENCRYPTION_KEY')
        os.environ['TOTP_ENCRYPTION_KEY'] = self.test_key
        
        # Test data
        self.test_secret = "JBSWY3DPEHPK3PXP"
        self.test_username = "testuser"
        self.test_issuer = "Test Service"
        
    def tearDown(self):
        """Clean up test environment"""
        if self.original_key:
            os.environ['TOTP_ENCRYPTION_KEY'] = self.original_key
        elif 'TOTP_ENCRYPTION_KEY' in os.environ:
            del os.environ['TOTP_ENCRYPTION_KEY']
    
    def test_generate_encryption_key(self):
        """Test encryption key generation"""
        key = fa_utils.generate_encryption_key()
        self.assertIsInstance(key, str)
        self.assertGreater(len(key), 0)
        
        # Test that generated keys are different
        key2 = fa_utils.generate_encryption_key()
        self.assertNotEqual(key, key2)
    
    def test_get_fernet_cipher(self):
        """Test Fernet cipher creation"""
        cipher = fa_utils.get_fernet_cipher()
        self.assertIsNotNone(cipher)
        
        # Test that cipher can encrypt and decrypt
        test_data = b"test data"
        encrypted = cipher.encrypt(test_data)
        decrypted = cipher.decrypt(encrypted)
        self.assertEqual(test_data, decrypted)
    
    def test_get_fernet_cipher_missing_key(self):
        """Test Fernet cipher creation with missing encryption key"""
        # Store original values
        original_key = os.environ.get('TOTP_ENCRYPTION_KEY')
        original_module_key = fa_utils.ENCRYPTION_KEY
        
        # Clear both environment and module variable
        if 'TOTP_ENCRYPTION_KEY' in os.environ:
            del os.environ['TOTP_ENCRYPTION_KEY']
        fa_utils.ENCRYPTION_KEY = None
        
        try:
            with self.assertRaises(ValueError) as context:
                fa_utils.get_fernet_cipher()
            self.assertIn("TOTP_ENCRYPTION_KEY environment variable not set", str(context.exception))
        finally:
            # Restore both values
            if original_key:
                os.environ['TOTP_ENCRYPTION_KEY'] = original_key
            fa_utils.ENCRYPTION_KEY = original_module_key
    
    def test_encrypt_decrypt_totp_secret(self):
        """Test TOTP secret encryption and decryption"""
        # Test encryption
        encrypted = fa_utils.encrypt_totp_secret(self.test_secret)
        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, self.test_secret)
        
        # Test decryption
        decrypted = fa_utils.decrypt_totp_secret(encrypted)
        self.assertEqual(decrypted, self.test_secret)
        
        # Test that same secret produces different encrypted output (due to salt)
        encrypted2 = fa_utils.encrypt_totp_secret(self.test_secret)
        self.assertNotEqual(encrypted, encrypted2)
        
        # Both should decrypt to the same value
        decrypted2 = fa_utils.decrypt_totp_secret(encrypted2)
        self.assertEqual(decrypted2, self.test_secret)
    
    def test_encrypt_totp_secret_missing_key(self):
        """Test encryption with missing key"""
        # Store original values
        original_key = os.environ.get('TOTP_ENCRYPTION_KEY')
        original_module_key = fa_utils.ENCRYPTION_KEY
        
        # Clear both environment and module variable
        if 'TOTP_ENCRYPTION_KEY' in os.environ:
            del os.environ['TOTP_ENCRYPTION_KEY']
        fa_utils.ENCRYPTION_KEY = None
        
        try:
            with self.assertRaises(Exception) as context:
                fa_utils.encrypt_totp_secret(self.test_secret)
            self.assertIn("TOTP_ENCRYPTION_KEY environment variable not set", str(context.exception))
        finally:
            # Restore both values
            if original_key:
                os.environ['TOTP_ENCRYPTION_KEY'] = original_key
            fa_utils.ENCRYPTION_KEY = original_module_key
    
    def test_decrypt_totp_secret_invalid_data(self):
        """Test decryption with invalid data"""
        with self.assertRaises(Exception):
            fa_utils.decrypt_totp_secret("invalid_base64_data")
    
    def test_generate_totp_secret(self):
        """Test TOTP secret generation"""
        secret = fa_utils.generate_totp_secret()
        self.assertIsInstance(secret, str)
        self.assertGreater(len(secret), 0)
        
        # Test that generated secrets are different
        secret2 = fa_utils.generate_totp_secret()
        self.assertNotEqual(secret, secret2)
        
        # Test that secrets are valid base32
        self.assertTrue(fa_utils.validate_totp_secret(secret))
        self.assertTrue(fa_utils.validate_totp_secret(secret2))
    
    def test_generate_backup_codes(self):
        """Test backup code generation"""
        codes = fa_utils.generate_backup_codes()
        self.assertEqual(len(codes), 10)  # Default count
        
        # Test custom count
        codes_custom = fa_utils.generate_backup_codes(5)
        self.assertEqual(len(codes_custom), 5)
        
        # Test code format (8 characters, alphanumeric)
        for code in codes:
            self.assertEqual(len(code), 8)
            self.assertTrue(code.isalnum())
            self.assertTrue(code.isupper())
        
        # Test that codes are unique
        self.assertEqual(len(set(codes)), len(codes))
    
    def test_hash_backup_code(self):
        """Test backup code hashing"""
        code = "ABC12345"
        hashed = fa_utils.hash_backup_code(code)
        
        self.assertIsInstance(hashed, str)
        self.assertNotEqual(hashed, code)
        
        # Test that same code produces different hash (due to salt)
        hashed2 = fa_utils.hash_backup_code(code)
        self.assertNotEqual(hashed, hashed2)
    
    def test_verify_backup_code(self):
        """Test backup code verification"""
        code = "ABC12345"
        hashed = fa_utils.hash_backup_code(code)
        
        # Test valid code
        is_valid, used_hash = fa_utils.verify_backup_code(code, [hashed])
        self.assertTrue(is_valid)
        self.assertEqual(used_hash, hashed)
        
        # Test invalid code
        is_valid, used_hash = fa_utils.verify_backup_code("INVALID", [hashed])
        self.assertFalse(is_valid)
        self.assertIsNone(used_hash)
        
        # Test with multiple hashes
        code2 = "XYZ98765"
        hashed2 = fa_utils.hash_backup_code(code2)
        hashes = [hashed, hashed2]
        
        is_valid, used_hash = fa_utils.verify_backup_code(code, hashes)
        self.assertTrue(is_valid)
        self.assertEqual(used_hash, hashed)
        
        is_valid, used_hash = fa_utils.verify_backup_code(code2, hashes)
        self.assertTrue(is_valid)
        self.assertEqual(used_hash, hashed2)
    
    def test_generate_qr_code(self):
        """Test QR code generation"""
        qr_data = fa_utils.generate_qr_code(
            self.test_secret, 
            self.test_username, 
            self.test_issuer
        )
        
        self.assertIsInstance(qr_data, bytes)
        self.assertGreater(len(qr_data), 0)
        
        # Verify it's a valid PNG image
        self.assertTrue(qr_data.startswith(b'\x89PNG\r\n\x1a\n'))
    
    def test_verify_totp_code(self):
        """Test TOTP code verification"""
        # Get current TOTP code
        current_code = fa_utils.get_current_totp_code(self.test_secret)
        
        # Test valid code
        self.assertTrue(fa_utils.verify_totp_code(self.test_secret, current_code))
        
        # Test invalid code
        self.assertFalse(fa_utils.verify_totp_code(self.test_secret, "000000"))
        
        # Test with different window
        self.assertTrue(fa_utils.verify_totp_code(self.test_secret, current_code, window=2))
    
    def test_verify_totp_code_invalid_secret(self):
        """Test TOTP verification with invalid secret"""
        self.assertFalse(fa_utils.verify_totp_code("invalid_secret", "123456"))
    
    def test_parse_serialize_backup_codes_hash(self):
        """Test backup codes hash parsing and serialization"""
        codes = ["ABC12345", "XYZ98765", "DEF45678"]
        hashes = [fa_utils.hash_backup_code(code) for code in codes]
        
        # Test serialization
        serialized = fa_utils.serialize_backup_codes_hash(hashes)
        self.assertIsInstance(serialized, str)
        
        # Test parsing
        parsed = fa_utils.parse_backup_codes_hash(serialized)
        self.assertEqual(parsed, hashes)
        
        # Test parsing invalid JSON
        parsed_invalid = fa_utils.parse_backup_codes_hash("invalid_json")
        self.assertEqual(parsed_invalid, [])
        
        # Test parsing None
        parsed_none = fa_utils.parse_backup_codes_hash(None)
        self.assertEqual(parsed_none, [])
    
    def test_remove_used_backup_code(self):
        """Test removing used backup codes"""
        codes = ["ABC12345", "XYZ98765", "DEF45678"]
        hashes = [fa_utils.hash_backup_code(code) for code in codes]
        serialized = fa_utils.serialize_backup_codes_hash(hashes)
        
        # Remove a used code
        updated = fa_utils.remove_used_backup_code(serialized, hashes[1])
        updated_parsed = fa_utils.parse_backup_codes_hash(updated)
        
        # Should have one less code
        self.assertEqual(len(updated_parsed), len(hashes) - 1)
        self.assertNotIn(hashes[1], updated_parsed)
        self.assertIn(hashes[0], updated_parsed)
        self.assertIn(hashes[2], updated_parsed)
    
    def test_get_totp_uri(self):
        """Test TOTP URI generation"""
        uri = fa_utils.get_totp_uri(self.test_secret, self.test_username, self.test_issuer)
        
        self.assertIsInstance(uri, str)
        self.assertIn("otpauth://totp/", uri)
        self.assertIn(self.test_username, uri)
        # Check for URL-encoded issuer (spaces become %20)
        self.assertIn("Test%20Service", uri)
        self.assertIn(self.test_secret, uri)
    
    def test_validate_totp_secret(self):
        """Test TOTP secret validation"""
        # Test valid secret
        self.assertTrue(fa_utils.validate_totp_secret(self.test_secret))
        
        # Test invalid secrets
        self.assertFalse(fa_utils.validate_totp_secret("invalid"))
        self.assertFalse(fa_utils.validate_totp_secret(""))
        self.assertFalse(fa_utils.validate_totp_secret("123456789"))
    
    def test_get_current_totp_code(self):
        """Test current TOTP code generation"""
        code = fa_utils.get_current_totp_code(self.test_secret)
        
        self.assertIsInstance(code, str)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        
        # Should be verifiable
        self.assertTrue(fa_utils.verify_totp_code(self.test_secret, code))
    
    def test_constants(self):
        """Test that constants are properly defined"""
        self.assertEqual(fa_utils.BACKUP_CODE_LENGTH, 8)
        self.assertEqual(fa_utils.TOTP_DIGITS, 6)
        self.assertEqual(fa_utils.TOTP_PERIOD, 30)
        self.assertEqual(fa_utils.TOTP_WINDOW, 1)
        self.assertIsInstance(fa_utils.BACKUP_CODE_CHARS, str)
        self.assertGreater(len(fa_utils.BACKUP_CODE_CHARS), 0)
    
    def test_error_messages(self):
        """Test that error messages are defined"""
        self.assertIsInstance(fa_utils.ERROR_ENCRYPTION_KEY_MISSING, str)
        self.assertIsInstance(fa_utils.ERROR_ENCRYPTION_FAILED, str)
        self.assertIsInstance(fa_utils.ERROR_DECRYPTION_FAILED, str)
        self.assertIsInstance(fa_utils.ERROR_INVALID_SECRET, str)
        self.assertIsInstance(fa_utils.ERROR_INVALID_CODE, str)
        self.assertIsInstance(fa_utils.ERROR_BACKUP_CODE_INVALID, str)
        self.assertIsInstance(fa_utils.ERROR_BACKUP_CODE_USED, str)


class Test2FAUtilsIntegration(unittest.TestCase):
    """Integration tests for 2FA utilities"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_key = "test_encryption_key_32_chars_long!"
        self.original_key = os.environ.get('TOTP_ENCRYPTION_KEY')
        os.environ['TOTP_ENCRYPTION_KEY'] = self.test_key
        
    def tearDown(self):
        """Clean up test environment"""
        if self.original_key:
            os.environ['TOTP_ENCRYPTION_KEY'] = self.original_key
        elif 'TOTP_ENCRYPTION_KEY' in os.environ:
            del os.environ['TOTP_ENCRYPTION_KEY']
    
    def test_full_2fa_setup_flow(self):
        """Test complete 2FA setup flow"""
        # 1. Generate TOTP secret
        secret = fa_utils.generate_totp_secret()
        self.assertTrue(fa_utils.validate_totp_secret(secret))
        
        # 2. Encrypt secret for storage
        encrypted_secret = fa_utils.encrypt_totp_secret(secret)
        self.assertNotEqual(encrypted_secret, secret)
        
        # 3. Generate QR code
        qr_data = fa_utils.generate_qr_code(secret, "testuser", "Test Service")
        self.assertIsInstance(qr_data, bytes)
        
        # 4. Generate backup codes
        backup_codes = fa_utils.generate_backup_codes(5)
        self.assertEqual(len(backup_codes), 5)
        
        # 5. Hash backup codes for storage
        backup_hashes = [fa_utils.hash_backup_code(code) for code in backup_codes]
        serialized_hashes = fa_utils.serialize_backup_codes_hash(backup_hashes)
        
        # 6. Verify TOTP code
        current_code = fa_utils.get_current_totp_code(secret)
        self.assertTrue(fa_utils.verify_totp_code(secret, current_code))
        
        # 7. Verify backup code
        is_valid, used_hash = fa_utils.verify_backup_code(backup_codes[0], backup_hashes)
        self.assertTrue(is_valid)
        
        # 8. Remove used backup code
        updated_hashes = fa_utils.remove_used_backup_code(serialized_hashes, used_hash)
        updated_parsed = fa_utils.parse_backup_codes_hash(updated_hashes)
        self.assertEqual(len(updated_parsed), len(backup_hashes) - 1)
        
        # 9. Decrypt secret for verification
        decrypted_secret = fa_utils.decrypt_totp_secret(encrypted_secret)
        self.assertEqual(decrypted_secret, secret)
    
    def test_backup_code_recovery_flow(self):
        """Test backup code recovery flow"""
        # Generate backup codes
        codes = fa_utils.generate_backup_codes(3)
        hashes = [fa_utils.hash_backup_code(code) for code in codes]
        serialized = fa_utils.serialize_backup_codes_hash(hashes)
        
        # Simulate using backup codes one by one
        for i, code in enumerate(codes):
            # Verify code
            is_valid, used_hash = fa_utils.verify_backup_code(code, hashes)
            self.assertTrue(is_valid)
            
            # Remove used code
            serialized = fa_utils.remove_used_backup_code(serialized, used_hash)
            hashes = fa_utils.parse_backup_codes_hash(serialized)
            
            # Should have fewer codes remaining
            self.assertEqual(len(hashes), len(codes) - i - 1)
        
        # All codes should be used
        self.assertEqual(len(hashes), 0)
    
    def test_totp_time_window_verification(self):
        """Test TOTP verification across time windows"""
        secret = fa_utils.generate_totp_secret()
        
        # Get current code
        current_code = fa_utils.get_current_totp_code(secret)
        
        # Should be valid with default window
        self.assertTrue(fa_utils.verify_totp_code(secret, current_code))
        
        # Should be valid with larger window
        self.assertTrue(fa_utils.verify_totp_code(secret, current_code, window=2))
        
        # Invalid code should not be valid
        self.assertFalse(fa_utils.verify_totp_code(secret, "000000"))


if __name__ == '__main__':
    # Create test suite using modern approach
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add test cases using modern method
    test_suite.addTests(loader.loadTestsFromTestCase(Test2FAUtils))
    test_suite.addTests(loader.loadTestsFromTestCase(Test2FAUtilsIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(not result.wasSuccessful())
