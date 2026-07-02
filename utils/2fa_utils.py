#!/usr/bin/env python3
"""
2FA Utility Functions
Core functions for two-factor authentication implementation
"""

import os
import secrets
import base64
import json
from typing import List, Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import bcrypt
import pyotp
import qrcode
from io import BytesIO

# Environment variable for encryption key (should be set in production)
ENCRYPTION_KEY = os.getenv('TOTP_ENCRYPTION_KEY')

def generate_encryption_key() -> str:
    """Generate a new encryption key for TOTP secrets"""
    return Fernet.generate_key().decode()

def get_fernet_cipher() -> Fernet:
    """Get Fernet cipher instance for encryption/decryption"""
    if not ENCRYPTION_KEY:
        raise ValueError("TOTP_ENCRYPTION_KEY environment variable not set")
    
    # Generate a proper Fernet key from the environment variable
    # Use PBKDF2 to derive a 32-byte key from the environment variable
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'2fa_salt',  # Fixed salt for consistency
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(ENCRYPTION_KEY.encode()))
    
    return Fernet(key)

def encrypt_totp_secret(secret: str) -> str:
    """
    Encrypt TOTP secret before storing in database
    
    Args:
        secret: Plain text TOTP secret
        
    Returns:
        Encrypted secret as base64 string
        
    Raises:
        ValueError: If encryption key is not configured
        Exception: If encryption fails
    """
    try:
        cipher = get_fernet_cipher()
        encrypted = cipher.encrypt(secret.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        raise Exception(f"Failed to encrypt TOTP secret: {e}")

def decrypt_totp_secret(encrypted_secret: str) -> str:
    """
    Decrypt TOTP secret from database
    
    Args:
        encrypted_secret: Encrypted secret as base64 string
        
    Returns:
        Plain text TOTP secret
        
    Raises:
        ValueError: If encryption key is not configured
        Exception: If decryption fails
    """
    try:
        cipher = get_fernet_cipher()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_secret)
        decrypted = cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        raise Exception(f"Failed to decrypt TOTP secret: {e}")

def generate_totp_secret() -> str:
    """
    Generate a new TOTP secret key
    
    Returns:
        Base32 encoded TOTP secret
    """
    return pyotp.random_base32()

def generate_backup_codes(count: int = 10) -> List[str]:
    """
    Generate random backup codes for account recovery
    
    Args:
        count: Number of backup codes to generate (default: 10)
        
    Returns:
        List of backup codes (8-character alphanumeric)
    """
    codes = []
    for _ in range(count):
        # Generate 8-character alphanumeric codes
        code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))
        codes.append(code)
    return codes

def hash_backup_code(code: str) -> str:
    """
    Hash a backup code using bcrypt
    
    Args:
        code: Plain text backup code
        
    Returns:
        Bcrypt hash of the code
    """
    return bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()

def verify_backup_code(input_code: str, stored_hashes: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Verify a backup code against stored hashes
    
    Args:
        input_code: User-provided backup code
        stored_hashes: List of stored bcrypt hashes
        
    Returns:
        Tuple of (is_valid, used_hash) where used_hash is the hash that matched
    """
    for stored_hash in stored_hashes:
        try:
            if bcrypt.checkpw(input_code.encode(), stored_hash.encode()):
                return True, stored_hash
        except Exception:
            continue
    return False, None

def generate_qr_code(secret: str, username: str, issuer: str = "AFROTC 695") -> bytes:
    """
    Generate QR code for TOTP setup
    
    Args:
        secret: TOTP secret key
        username: User's username or email
        issuer: Service name (default: "AFROTC 695")
        
    Returns:
        QR code image as PNG bytes
    """
    # Create TOTP URI
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=username,
        issuer_name=issuer
    )
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    return img_buffer.getvalue()

def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    """
    Verify a TOTP code
    
    Args:
        secret: TOTP secret key
        code: 6-digit code from authenticator app
        window: Time window for verification (default: 1)
        
    Returns:
        True if code is valid, False otherwise
    """
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)
    except Exception:
        return False

def parse_backup_codes_hash(backup_codes_hash: str) -> List[str]:
    """
    Parse backup codes hash from database
    
    Args:
        backup_codes_hash: JSON string of backup code hashes
        
    Returns:
        List of backup code hashes
    """
    try:
        return json.loads(backup_codes_hash)
    except (json.JSONDecodeError, TypeError):
        return []

def serialize_backup_codes_hash(backup_codes: List[str]) -> str:
    """
    Serialize backup codes hash for database storage
    
    Args:
        backup_codes: List of backup code hashes
        
    Returns:
        JSON string of backup code hashes
    """
    return json.dumps(backup_codes)

def remove_used_backup_code(backup_codes_hash: str, used_hash: str) -> str:
    """
    Remove a used backup code from the stored hashes
    
    Args:
        backup_codes_hash: Current backup codes hash JSON string
        used_hash: Hash of the used backup code
        
    Returns:
        Updated backup codes hash JSON string
    """
    codes = parse_backup_codes_hash(backup_codes_hash)
    if used_hash in codes:
        codes.remove(used_hash)
    return serialize_backup_codes_hash(codes)

def get_totp_uri(secret: str, username: str, issuer: str = "AFROTC 695") -> str:
    """
    Get TOTP provisioning URI for manual entry
    
    Args:
        secret: TOTP secret key
        username: User's username or email
        issuer: Service name
        
    Returns:
        TOTP provisioning URI
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)

def validate_totp_secret(secret: str) -> bool:
    """
    Validate TOTP secret format
    
    Args:
        secret: TOTP secret to validate
        
    Returns:
        True if secret is valid, False otherwise
    """
    try:
        # Check if it's valid base32 and has proper length
        if not secret or len(secret) < 16:
            return False
        
        # Try to create TOTP object
        totp = pyotp.TOTP(secret)
        # Verify it can generate a code
        totp.now()
        return True
    except Exception:
        return False

def get_current_totp_code(secret: str) -> str:
    """
    Get current TOTP code for testing purposes
    
    Args:
        secret: TOTP secret key
        
    Returns:
        Current 6-digit TOTP code
    """
    totp = pyotp.TOTP(secret)
    return totp.now()

# Security constants
BACKUP_CODE_LENGTH = 8
BACKUP_CODE_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
TOTP_DIGITS = 6
TOTP_PERIOD = 30  # seconds
TOTP_WINDOW = 1   # time windows for verification

# Error messages
ERROR_ENCRYPTION_KEY_MISSING = "TOTP encryption key not configured"
ERROR_ENCRYPTION_FAILED = "Failed to encrypt TOTP secret"
ERROR_DECRYPTION_FAILED = "Failed to decrypt TOTP secret"
ERROR_INVALID_SECRET = "Invalid TOTP secret format"
ERROR_INVALID_CODE = "Invalid TOTP code"
ERROR_BACKUP_CODE_INVALID = "Invalid backup code"
ERROR_BACKUP_CODE_USED = "Backup code already used"
