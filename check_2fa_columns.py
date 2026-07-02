#!/usr/bin/env python3
"""
Check if 2FA columns exist in the database
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv('env.local')

def check_2fa_columns():
    """Check if 2FA columns exist in the User table"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ Error: DATABASE_URL not found in environment variables")
        return False
    
    # Convert postgres:// to postgresql:// for SQLAlchemy compatibility
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        # Connect to database
        print("📡 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check for 2FA columns
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'user' 
            AND (column_name LIKE '%totp%' OR column_name LIKE '%backup%' OR column_name LIKE '%2fa%')
            ORDER BY column_name
        """)
        
        columns = cursor.fetchall()
        
        print("\n📊 2FA Columns Status:")
        print("-" * 50)
        
        if columns:
            for column in columns:
                print(f"✅ {column[0]}: {column[1]} (nullable: {column[2]}, default: {column[3]})")
            print(f"\n✅ Found {len(columns)} 2FA columns")
            return True
        else:
            print("❌ No 2FA columns found")
            return False
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_2fa_columns()
