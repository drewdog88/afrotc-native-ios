#!/usr/bin/env python3
"""
Advanced migration script that handles schema differences between SQLite and PostgreSQL
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
        print("❌ Error: DATABASE_URL not found in .env file")
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
        print(f"❌ Error: Backup file {backup_file} not found")
        sys.exit(1)
    
    return sqlite3.connect(backup_file)

def get_table_data_with_mapping(sqlite_conn, sqlite_table, column_mapping=None):
    """Get data from SQLite table with column mapping"""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {sqlite_table}")
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    
    if column_mapping:
        # Map column names
        mapped_columns = []
        for col in columns:
            mapped_col = column_mapping.get(col, col)
            if mapped_col:  # Skip None values (columns to exclude)
                mapped_columns.append(mapped_col)
        
        # Map row data
        mapped_rows = []
        for row in rows:
            mapped_row = []
            for i, col in enumerate(columns):
                mapped_col = column_mapping.get(col, col)
                if mapped_col:  # Skip None values
                    mapped_row.append(row[i])
            mapped_rows.append(tuple(mapped_row))
        
        return mapped_columns, mapped_rows
    
    return columns, rows

def insert_data_with_conflict_handling(neon_engine, table_name, columns, rows, conflict_strategy='skip'):
    """Insert data into Neon PostgreSQL table with conflict handling"""
    if not rows:
        print(f"   No data to insert for table {table_name}")
        return 0
    
    # Create column list for INSERT statement (PostgreSQL style with quotes)
    column_list = ', '.join([f'"{col}"' for col in columns])
    placeholders = ', '.join(['%s'] * len(columns))
    
    # Handle conflicts for tables with unique constraints
    if conflict_strategy == 'skip':
        insert_sql = f'INSERT INTO "{table_name}" ({column_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
    elif conflict_strategy == 'update':
        # For user table, update on conflict
        update_clause = ', '.join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col != 'id'])
        insert_sql = f'INSERT INTO "{table_name}" ({column_list}) VALUES ({placeholders}) ON CONFLICT (id) DO UPDATE SET {update_clause}'
    else:
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
                print(f"   ⚠️  Row skipped due to error: {str(e)[:100]}...")
                continue
        
        raw_conn.commit()
        return inserted_count
    except Exception as e:
        print(f"   ❌ Error during batch insert: {e}")
        raw_conn.rollback()
        return 0
    finally:
        cursor.close()
        raw_conn.close()

def main():
    """Main migration function with schema mapping"""
    print("🚀 Starting SMART data migration from SQLite to Neon PostgreSQL...")
    print("=" * 70)
    
    # Use the current database file
    backup_file = "instance/afrotc695.db"
    
    if not os.path.exists(backup_file):
        print(f"❌ Error: Database file {backup_file} not found")
        return False
    
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
        return False
    
    # Define schema mappings between SQLite and PostgreSQL
    # Format: sqlite_table -> (postgres_table, column_mapping, conflict_strategy)
    table_mappings = {
        # Map SQLite 'user' to PostgreSQL 'user' (reserved word handling)
        'user': ('user', {
            'id': 'id',
            'username': 'username', 
            'email': 'email',
            'password_hash': 'password_hash',
            'role': 'role',
            'created_at': 'created_at',
            'last_login': 'last_login',
            'is_active': 'is_active',
            'password_history': 'password_history',
            'failed_login_attempts': 'failed_login_attempts',
            'locked_until': 'locked_until'
        }, 'skip'),
        
        # Map SQLite 'cadet' to PostgreSQL 'cadet' 
        'cadet': ('cadet', {
            'id': 'id',
            'first_name': 'first_name',
            'last_name': 'last_name', 
            'email': 'email',
            'phone': 'phone',
            'major': 'major',
            'graduation_year': 'class_year',  # Map graduation_year -> class_year
            'rank': 'rank',
            'hometown': None,  # Skip this column (doesn't exist in PostgreSQL)
            'track': None,     # Skip this column
            'status': 'status',
            'notes': 'notes',
            'gpa': 'gpa',
            'created_at': 'created_at',
            'updated_at': 'updated_at'
        }, 'skip'),
        
        # Map SQLite 'university_contact' to PostgreSQL 'contact'
        'university_contact': ('contact', {
            'id': 'id',
            'university_name': 'organization',  # Map university_name -> organization
            'contact_name': 'name',             # Map contact_name -> name
            'contact_title': 'title',           # Map contact_title -> title
            'email': 'email',
            'phone': 'phone', 
            'address': 'address',
            'notes': 'notes',
            'created_at': 'created_at',
            'updated_at': 'updated_at'
        }, 'skip'),
        
        # Map SQLite 'external_link' to PostgreSQL 'external_link'
        'external_link': ('external_link', {
            'id': 'id',
            'title': 'title',
            'url': 'url',
            'description': 'description',
            'category': 'category',
            'is_active': None,    # Skip this column (doesn't exist in PostgreSQL)
            'sort_order': None,   # Skip this column
            'created_at': 'created_at',
            'updated_at': 'updated_at'
        }, 'skip'),
        
        # Map SQLite 'activity_log' to PostgreSQL 'activity_log'
        'activity_log': ('activity_log', {
            'id': 'id',
            'user_id': 'user_id',
            'username': None,      # Skip this column (doesn't exist in PostgreSQL)
            'action': 'action',
            'table_name': None,    # Skip this column
            'record_id': None,     # Skip this column  
            'description': 'details',  # Map description -> details
            'additional_info': None,   # Skip this column
            'ip_address': 'ip_address',
            'user_agent': 'user_agent',
            'created_at': 'created_at'
        }, 'skip')
    }
    
    total_migrated = 0
    migration_summary = []
    
    print("\n📊 Migration Plan with Schema Mapping:")
    print("-" * 50)
    
    # Check what we can migrate
    for sqlite_table, (postgres_table, column_mapping, conflict_strategy) in table_mappings.items():
        try:
            columns, rows = get_table_data_with_mapping(sqlite_conn, sqlite_table, column_mapping)
            
            # Check if target table exists
            inspector = inspect(neon_engine)
            existing_tables = inspector.get_table_names()
            table_exists = postgres_table in existing_tables
            
            status = "✅ Ready" if table_exists else "❌ Missing"
            print(f"  {sqlite_table} -> {postgres_table}: {len(rows)} records | {status}")
            
        except Exception as e:
            print(f"  {sqlite_table}: Error reading - {e}")
    
    print("\n🔄 Starting Smart Migration:")
    print("-" * 50)
    
    for sqlite_table, (postgres_table, column_mapping, conflict_strategy) in table_mappings.items():
        try:
            print(f"\n📋 Processing: {sqlite_table} -> {postgres_table}")
            
            # Check if target table exists
            inspector = inspect(neon_engine)
            existing_tables = inspector.get_table_names()
            if postgres_table not in existing_tables:
                print(f"   ⚠️  Target table '{postgres_table}' doesn't exist, skipping...")
                migration_summary.append(f"{sqlite_table} -> {postgres_table}: SKIPPED (table missing)")
                continue
            
            # Get mapped data
            columns, rows = get_table_data_with_mapping(sqlite_conn, sqlite_table, column_mapping)
            print(f"   📊 Found {len(rows)} records to migrate")
            print(f"   🗂️  Mapped columns: {columns}")
            
            if rows:
                # Insert with conflict handling
                migrated_count = insert_data_with_conflict_handling(
                    neon_engine, postgres_table, columns, rows, conflict_strategy
                )
                print(f"   ✅ Successfully migrated {migrated_count}/{len(rows)} records")
                total_migrated += migrated_count
                migration_summary.append(f"{sqlite_table} -> {postgres_table}: {migrated_count} records")
            else:
                print(f"   ℹ️  No data to migrate")
                migration_summary.append(f"{sqlite_table} -> {postgres_table}: 0 records (empty)")
                
        except Exception as e:
            print(f"   ❌ Error migrating {sqlite_table}: {e}")
            migration_summary.append(f"{sqlite_table} -> {postgres_table}: FAILED - {e}")
            continue
    
    sqlite_conn.close()
    
    print("\n" + "=" * 70)
    print("🎉 SMART MIGRATION COMPLETED!")
    print("=" * 70)
    print(f"📊 Total records migrated: {total_migrated}")
    print(f"📂 Source database: {backup_file}")
    print(f"🎯 Target: Neon PostgreSQL")
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n📋 Migration Summary:")
    print("-" * 50)
    for summary in migration_summary:
        print(f"  {summary}")
    
    if total_migrated > 0:
        print(f"\n✅ SUCCESS! Your data has been preserved and migrated!")
        print(f"🔐 You can now log in with your existing admin credentials.")
        print(f"🌟 The Vercel application should now work properly with your data!")
    else:
        print(f"\n⚠️  No data was migrated. Please check the error messages above.")
    
    return total_migrated > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
