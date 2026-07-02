#!/usr/bin/env python3
"""
Script to check and fix production database schema issues
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

def get_database_connection():
    """Get connection to production database"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    # Convert postgres:// to postgresql:// for psycopg2
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def check_user_table_schema(conn):
    """Check if User table has all required columns"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check for required columns
    required_columns = {
        'password_hash': 'VARCHAR(255)',
        'secret_answer_hash': 'VARCHAR(255)',
        'failed_login_attempts': 'INTEGER',
        'totp_secret': 'VARCHAR(255)',
        'totp_enabled': 'BOOLEAN',
        'backup_codes_hash': 'TEXT',
        'totp_setup_completed': 'BOOLEAN',
        'can_enable_2fa': 'BOOLEAN'
    }
    
    missing_columns = []
    wrong_type_columns = []
    
    for column, expected_type in required_columns.items():
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'user' AND column_name = %s
        """, (column,))
        
        result = cursor.fetchone()
        if not result:
            missing_columns.append(column)
        else:
            # Check if type is correct
            actual_type = result['data_type']
            if 'character_maximum_length' in result and result['character_maximum_length']:
                actual_type += f"({result['character_maximum_length']})"
            
            if expected_type.lower() not in actual_type.lower():
                wrong_type_columns.append((column, expected_type, actual_type))
    
    cursor.close()
    return missing_columns, wrong_type_columns

def apply_migrations(conn):
    """Apply missing migrations to the database"""
    cursor = conn.cursor()
    
    print("Applying migrations...")
    
    # Migration 1: Update password hash lengths
    try:
        cursor.execute("ALTER TABLE \"user\" ALTER COLUMN password_hash TYPE VARCHAR(255)")
        cursor.execute("ALTER TABLE \"user\" ALTER COLUMN secret_answer_hash TYPE VARCHAR(255)")
        cursor.execute("ALTER TABLE password_history ALTER COLUMN password_hash TYPE VARCHAR(255)")
        print("✓ Updated password hash field lengths")
    except Exception as e:
        print(f"⚠ Password hash migration: {e}")
    
    # Migration 2: Add missing columns
    migrations = [
        ("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0", "failed_login_attempts"),
        ("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(255)", "totp_secret"),
        ("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE", "totp_enabled"),
        ("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS backup_codes_hash TEXT", "backup_codes_hash"),
        ("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS totp_setup_completed BOOLEAN DEFAULT FALSE", "totp_setup_completed"),
        ("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS can_enable_2fa BOOLEAN DEFAULT TRUE", "can_enable_2fa")
    ]
    
    for sql, column_name in migrations:
        try:
            cursor.execute(sql)
            print(f"✓ Added column: {column_name}")
        except Exception as e:
            print(f"⚠ Column {column_name}: {e}")
    
    # Migration 3: Add indexes
    indexes = [
        ("CREATE INDEX IF NOT EXISTS idx_user_totp_enabled ON \"user\"(totp_enabled)", "totp_enabled index"),
        ("CREATE INDEX IF NOT EXISTS idx_user_can_enable_2fa ON \"user\"(can_enable_2fa)", "can_enable_2fa index")
    ]
    
    for sql, index_name in indexes:
        try:
            cursor.execute(sql)
            print(f"✓ Added index: {index_name}")
        except Exception as e:
            print(f"⚠ Index {index_name}: {e}")
    
    conn.commit()
    cursor.close()

def check_users(conn):
    """Check if there are any users in the database"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT COUNT(*) as count FROM \"user\"")
    result = cursor.fetchone()
    user_count = result['count']
    
    if user_count == 0:
        print("⚠ No users found in database")
        print("Creating default admin user...")
        
        from werkzeug.security import generate_password_hash
        cursor.execute("""
            INSERT INTO "user" (
                username, email, password_hash, first_name, last_name,
                secret_question, secret_answer_hash, role, is_active
            ) VALUES (
                'admin', 'admin@afrotc695.com', %s, 'Admin', 'User',
                'What is your favorite color?', %s, 'admin', TRUE
            )
        """, (
            generate_password_hash('admin123'),
            generate_password_hash('blue')
        ))
        
        conn.commit()
        print("✓ Created default admin user: username=admin, password=admin123")
    else:
        print(f"✓ Found {user_count} users in database")
    
    cursor.close()

def main():
    print("=== Production Database Check and Fix ===")
    
    # Connect to database
    conn = get_database_connection()
    print("✓ Connected to production database")
    
    # Check schema
    print("\n--- Checking User table schema ---")
    missing_columns, wrong_type_columns = check_user_table_schema(conn)
    
    if missing_columns:
        print(f"Missing columns: {', '.join(missing_columns)}")
    else:
        print("✓ All required columns present")
    
    if wrong_type_columns:
        print("Columns with wrong types:")
        for column, expected, actual in wrong_type_columns:
            print(f"  {column}: expected {expected}, got {actual}")
    else:
        print("✓ All column types correct")
    
    # Apply migrations if needed
    if missing_columns or wrong_type_columns:
        print("\n--- Applying migrations ---")
        apply_migrations(conn)
        
        # Re-check schema
        print("\n--- Re-checking schema ---")
        missing_columns, wrong_type_columns = check_user_table_schema(conn)
        if not missing_columns and not wrong_type_columns:
            print("✓ All migrations applied successfully")
        else:
            print("⚠ Some issues remain after migrations")
    else:
        print("✓ No migrations needed")
    
    # Check users
    print("\n--- Checking users ---")
    check_users(conn)
    
    conn.close()
    print("\n=== Database check complete ===")

if __name__ == "__main__":
    main()
