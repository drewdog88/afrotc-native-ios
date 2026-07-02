#!/usr/bin/env python3
"""
Quick script to check SQLite database contents
"""
import sqlite3
import os

def check_database():
    db_path = 'instance/afrotc695.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f"Database: {db_path}")
    print(f"Tables found: {len(tables)}")
    print()
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {table_name}: {count} records")
    
    conn.close()

if __name__ == "__main__":
    check_database()
