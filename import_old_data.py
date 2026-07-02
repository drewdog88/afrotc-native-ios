#!/usr/bin/env python3
"""
Script to import data from old SQLite backup into new MySQL database
"""

import sqlite3
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

def get_mysql_connection():
    """Get MySQL connection using environment variables"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not found in .env file")
        sys.exit(1)
    
    # Create engine
    engine = create_engine(database_url)
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

def insert_data_to_mysql(mysql_engine, table_name, columns, rows):
    """Insert data into MySQL table"""
    if not rows:
        print(f"No data to insert for table {table_name}")
        return 0
    
    # Create column list for INSERT statement
    column_list = ', '.join([f'`{col}`' for col in columns])
    placeholders = ', '.join(['%s'] * len(columns))
    
    # Prepare INSERT statement
    insert_sql = f"INSERT INTO `{table_name}` ({column_list}) VALUES ({placeholders})"
    
    # Execute insert for each row
    conn = mysql_engine.raw_connection()
    cursor = conn.cursor()
    try:
        for row in rows:
            try:
                cursor.execute(insert_sql, row)
            except Exception as e:
                print(f"Error inserting row {row}: {e}")
                continue
        conn.commit()
        return len(rows)
    finally:
        cursor.close()
        conn.close()

def main():
    """Main import function"""
    print("Starting data import from SQLite backup to MySQL...")
    
    # Use the most recent backup file
    backup_file = "backups/afrotc695_backup_20250804_075339.db"
    
    # Get connections
    sqlite_conn = get_sqlite_connection(backup_file)
    mysql_engine = get_mysql_connection()
    
    # Tables to import (excluding user table to preserve current users)
    tables_to_import = [
        'potential_recruit',
        'cadet', 
        'university_contact',
        'recruitment_event',
        'activity_log',
        'external_link',
        'recruitment_document'
    ]
    
    total_imported = 0
    
    for table_name in tables_to_import:
        try:
            print(f"\nProcessing table: {table_name}")
            
            # Get data from SQLite
            columns, rows = get_table_data(sqlite_conn, table_name)
            print(f"Found {len(rows)} records in {table_name}")
            
            if rows:
                # Insert into MySQL
                imported_count = insert_data_to_mysql(mysql_engine, table_name, columns, rows)
                print(f"Successfully imported {imported_count} records to {table_name}")
                total_imported += imported_count
            else:
                print(f"No data to import for {table_name}")
                
        except Exception as e:
            print(f"Error importing {table_name}: {e}")
            continue
    
    sqlite_conn.close()
    
    print(f"\nImport completed!")
    print(f"Total records imported: {total_imported}")
    print(f"Source backup: {backup_file}")

if __name__ == "__main__":
    main() 