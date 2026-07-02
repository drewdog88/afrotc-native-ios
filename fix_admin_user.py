#!/usr/bin/env python3
"""
Quick script to fix the admin user in production
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2

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

def fix_admin_user(conn):
    """Fix the admin user with proper first_name and last_name"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE "user" 
            SET first_name = 'Admin', last_name = 'User'
            WHERE username = 'admin'
        """)
        
        if cursor.rowcount > 0:
            print("✓ Fixed admin user first_name and last_name")
        else:
            print("⚠ Admin user not found")
        
        conn.commit()
    except Exception as e:
        print(f"⚠ Error fixing admin user: {e}")
    
    cursor.close()

def main():
    print("=== Fix Admin User ===")
    
    conn = get_database_connection()
    print("✓ Connected to production database")
    
    fix_admin_user(conn)
    
    conn.close()
    print("=== Admin user fix complete ===")

if __name__ == "__main__":
    main()
