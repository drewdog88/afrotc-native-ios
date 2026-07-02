#!/usr/bin/env python3
"""
Script to migrate data from SQLite backup to Neon PostgreSQL database
Adapted from import_old_data.py for PostgreSQL compatibility
"""

import sqlite3
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

def get_neon_connection():
    """Get Neon PostgreSQL connection using environment variables"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not found in .env file")
        sys.exit(1)
    
    # Handle postgres:// vs postgresql:// prefix
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # Create engine with SSL requirement for Neon
    connect_args = {"sslmode": "require"} if 'postgresql' in database_url else {}
    engine = create_engine(database_url, connect_args=connect_args)
    return engine

def get_sqlite_connection(backup_file):
    """Get SQLite connection to backup file"""
    if not os.path.exists(backup_file):
        print(f"Error: Backup file {backup_file} not found")
        sys.exit(1)
    
    return sqlite3.connect(backup_file)

def get_table_data(sqlite_conn, table_name):
    """Get all data from a SQLite table"""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    return columns, rows

def check_table_exists(neon_engine, table_name):
    """Check if table exists in Neon PostgreSQL"""
    inspector = inspect(neon_engine)
    existing_tables = inspector.get_table_names()
    return table_name in existing_tables

def clear_table_data(neon_engine, table_name):
    """Clear all data from a PostgreSQL table"""
    with neon_engine.connect() as conn:
        # Disable foreign key checks temporarily
        conn.execute(text(f"DELETE FROM {table_name}"))
        conn.commit()
        print(f"Cleared existing data from {table_name}")

def insert_data_to_neon(neon_engine, table_name, columns, rows):
    """Insert data into Neon PostgreSQL table"""
    if not rows:
        print(f"No data to insert for table {table_name}")
        return 0
    
    # Create column list for INSERT statement (PostgreSQL style)
    column_list = ', '.join([f'"{col}"' for col in columns])
    placeholders = ', '.join(['%s'] * len(columns))
    
    # Prepare INSERT statement
    insert_sql = f'INSERT INTO "{table_name}" ({column_list}) VALUES ({placeholders})'
    
    # Get raw psycopg2 connection for better PostgreSQL compatibility
    raw_conn = neon_engine.raw_connection()
    cursor = raw_conn.cursor()
    
    inserted_count = 0
    try:
        for row in rows:
            try:
                # Convert SQLite row to PostgreSQL compatible format
                converted_row = []
                for value in row:
                    if isinstance(value, str) and value == '':
                        # Convert empty strings to NULL for PostgreSQL
                        converted_row.append(None)
                    else:
                        converted_row.append(value)
                
                cursor.execute(insert_sql, converted_row)
                inserted_count += 1
            except Exception as e:
                print(f"Error inserting row {row}: {e}")
                continue
        
        raw_conn.commit()
        return inserted_count
    except Exception as e:
        print(f"Error during batch insert: {e}")
        raw_conn.rollback()
        return 0
    finally:
        cursor.close()
        raw_conn.close()

def main():
    """Main migration function"""
    print("🚀 Starting data migration from SQLite to Neon PostgreSQL...")
    print("=" * 60)
    
    # Use the current database file
    backup_file = "instance/afrotc695.db"
    
    if not os.path.exists(backup_file):
        print(f"❌ Error: Database file {backup_file} not found")
        print("Available database files:")
        for f in os.listdir("instance"):
            if f.endswith('.db'):
                print(f"  - instance/{f}")
        return
    
    # Get connections
    print(f"📂 Using database: {backup_file}")
    sqlite_conn = get_sqlite_connection(backup_file)
    neon_engine = get_neon_connection()
    
    # Test Neon connection
    try:
        with neon_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to Neon PostgreSQL: {version[:50]}...")
    except Exception as e:
        print(f"❌ Error connecting to Neon PostgreSQL: {e}")
        return
    
    # Tables to migrate (preserve order due to foreign keys)
    tables_to_migrate = [
        'user',                    # Must be first (referenced by others)
        'potential_recruit', 
        'cadet',
        'university_contact',
        'recruitment_event',
        'external_link',
        'recruitment_document',
        'activity_log',           # Last (references other tables)
        'password_history'        # Last (references user table)
    ]
    
    total_migrated = 0
    migration_summary = []
    
    print("\n📊 Migration Plan:")
    print("-" * 40)
    
    # First, check what tables exist and what data we have
    for table_name in tables_to_migrate:
        try:
            columns, rows = get_table_data(sqlite_conn, table_name)
            table_exists = check_table_exists(neon_engine, table_name)
            status = "✅ Ready" if table_exists else "❌ Missing"
            print(f"  {table_name}: {len(rows)} records | {status}")
        except Exception as e:
            print(f"  {table_name}: Error reading - {e}")
    
    print("\n🔄 Starting Migration:")
    print("-" * 40)
    
    for table_name in tables_to_migrate:
        try:
            print(f"\n📋 Processing table: {table_name}")
            
            # Check if table exists in Neon
            if not check_table_exists(neon_engine, table_name):
                print(f"⚠️  Warning: Table {table_name} doesn't exist in Neon PostgreSQL")
                print(f"   This suggests the database schema hasn't been initialized yet.")
                continue
            
            # Get data from SQLite
            columns, rows = get_table_data(sqlite_conn, table_name)
            print(f"   Found {len(rows)} records in SQLite")
            
            if rows:
                # Clear existing data in Neon (to avoid duplicates)
                clear_table_data(neon_engine, table_name)
                
                # Insert into Neon PostgreSQL
                migrated_count = insert_data_to_neon(neon_engine, table_name, columns, rows)
                print(f"   ✅ Successfully migrated {migrated_count}/{len(rows)} records")
                total_migrated += migrated_count
                migration_summary.append(f"{table_name}: {migrated_count} records")
            else:
                print(f"   ℹ️  No data to migrate for {table_name}")
                migration_summary.append(f"{table_name}: 0 records (empty)")
                
        except Exception as e:
            print(f"   ❌ Error migrating {table_name}: {e}")
            migration_summary.append(f"{table_name}: FAILED - {e}")
            continue
    
    sqlite_conn.close()
    
    print("\n" + "=" * 60)
    print("🎉 MIGRATION COMPLETED!")
    print("=" * 60)
    print(f"📊 Total records migrated: {total_migrated}")
    print(f"📂 Source database: {backup_file}")
    print(f"🎯 Target: Neon PostgreSQL")
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n📋 Migration Summary:")
    print("-" * 40)
    for summary in migration_summary:
        print(f"  {summary}")
    
    if total_migrated > 0:
        print(f"\n✅ Your data has been successfully preserved and migrated!")
        print(f"🔐 You can now log in with your existing admin credentials.")
    else:
        print(f"\n⚠️  No data was migrated. Please check the error messages above.")

if __name__ == "__main__":
    main()
