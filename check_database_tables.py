#!/usr/bin/env python3
"""
Script to check all tables in the database and compare with backup coverage
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

def check_database_tables(conn):
    """Check all tables in the database"""
    cursor = conn.cursor()
    
    print("=== DATABASE TABLE ANALYSIS ===")
    print()
    
    # Get all tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    
    all_tables = [row[0] for row in cursor.fetchall()]
    
    print(f"Total tables in database: {len(all_tables)}")
    print("All tables:")
    for i, table in enumerate(all_tables, 1):
        print(f"  {i}. {table}")
    print()
    
    # Check record counts for each table
    print("Record counts:")
    print("-" * 50)
    for table in all_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table:30} | {count:5} records")
        except Exception as e:
            print(f"{table:30} | ERROR: {e}")
    print()
    
    # Tables currently being backed up (from neon_backup_scheduler.py)
    backup_tables = [
        'user', 'potential_recruit', 'cadet', 'university_contact', 
        'recruitment_event', 'external_link', 'recruitment_document', 
        'activity_log', 'password_history'
    ]
    
    print("=== BACKUP COVERAGE ANALYSIS ===")
    print()
    
    # Check which tables are being backed up
    backed_up = [table for table in all_tables if table in backup_tables]
    not_backed_up = [table for table in all_tables if table not in backup_tables]
    
    print(f"Tables being backed up: {len(backed_up)}")
    for table in backed_up:
        print(f"  ✅ {table}")
    print()
    
    if not_backed_up:
        print(f"Tables NOT being backed up: {len(not_backed_up)}")
        for table in not_backed_up:
            print(f"  ❌ {table}")
        print()
        
        print("⚠️  WARNING: Some tables are not being backed up!")
        print("   This could result in data loss during restore operations.")
    else:
        print("✅ All tables are being backed up!")
    
    # Check for tables in backup list that don't exist
    missing_tables = [table for table in backup_tables if table not in all_tables]
    if missing_tables:
        print()
        print(f"Tables in backup list that don't exist: {len(missing_tables)}")
        for table in missing_tables:
            print(f"  ⚠️  {table}")
    
    cursor.close()
    
    return all_tables, backup_tables, not_backed_up, missing_tables

def main():
    print("=== Database Table and Backup Coverage Check ===")
    
    # Connect to database
    conn = get_database_connection()
    print("✓ Connected to production database")
    print()
    
    # Check tables and backup coverage
    all_tables, backup_tables, not_backed_up, missing_tables = check_database_tables(conn)
    
    conn.close()
    
    print()
    print("=== SUMMARY ===")
    print(f"Total database tables: {len(all_tables)}")
    print(f"Tables being backed up: {len(backup_tables)}")
    print(f"Tables NOT backed up: {len(not_backed_up)}")
    print(f"Missing tables: {len(missing_tables)}")
    
    if not_backed_up:
        print()
        print("🔧 RECOMMENDATION: Update neon_backup_scheduler.py to include:")
        for table in not_backed_up:
            print(f"   - '{table}'")

if __name__ == "__main__":
    main()
