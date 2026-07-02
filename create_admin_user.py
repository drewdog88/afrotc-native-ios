#!/usr/bin/env python3
"""
Script to create a proper admin user in production
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from werkzeug.security import generate_password_hash
from datetime import datetime

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

def create_admin_user(conn):
    """Create a proper admin user"""
    cursor = conn.cursor()
    
    try:
        # Check if admin user already exists
        cursor.execute('SELECT id FROM "user" WHERE username = %s', ('admin',))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print("✓ Admin user already exists")
            return
        
        # Create admin user
        cursor.execute("""
            INSERT INTO "user" (
                username, email, password_hash, first_name, last_name,
                phone, role, is_active, is_locked, failed_login_attempts,
                password_changed_at, force_password_change,
                secret_question, secret_answer_hash, totp_enabled,
                totp_setup_completed, can_enable_2fa, created_at, last_modified
            ) VALUES (
                'admin', 'admin@afrotc695.com', %s, 'Admin', 'User',
                NULL, 'admin', TRUE, FALSE, 0,
                %s, FALSE,
                'What is your favorite color?', %s, FALSE,
                FALSE, TRUE, %s, %s
            )
        """, (
            generate_password_hash('admin123'),
            datetime.utcnow(),
            generate_password_hash('blue'),
            datetime.utcnow(),
            datetime.utcnow()
        ))
        
        conn.commit()
        print("✓ Created admin user: username=admin, password=admin123")
        
    except Exception as e:
        print(f"⚠ Error creating admin user: {e}")
    
    cursor.close()

def main():
    print("=== Create Admin User ===")
    
    conn = get_database_connection()
    print("✓ Connected to production database")
    
    create_admin_user(conn)
    
    conn.close()
    print("=== Admin user creation complete ===")

if __name__ == "__main__":
    main()
