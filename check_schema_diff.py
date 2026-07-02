#!/usr/bin/env python3
"""
Check schema differences between backup and current database
"""

import sqlite3
from api.app import app, db
from sqlalchemy import text

def check_schema_diff():
    print("🔍 Checking schema differences...")
    
    # Check backup schema
    print("\n📋 Backup Schema (SQLite):")
    conn = sqlite3.connect('instance/afrotc695_backup_20250803_234949.db')
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(user)")
    backup_cols = cursor.fetchall()
    print("User table columns:")
    for col in backup_cols:
        print(f"  {col[1]} ({col[2]}) - nullable: {col[3]}")
    
    # Check current schema
    print("\n📋 Current Schema (PostgreSQL):")
    with app.app_context():
        result = db.session.execute(text("""
            SELECT column_name, is_nullable, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'user' 
            ORDER BY ordinal_position
        """))
        current_cols = result.fetchall()
        print("User table columns:")
        for col in current_cols:
            print(f"  {col[0]} ({col[2]}) - nullable: {col[1]}")
    
    conn.close()
    
    # Show differences
    print("\n🔍 Schema Differences:")
    backup_col_names = [col[1] for col in backup_cols]
    current_col_names = [col[0] for col in current_cols]
    
    missing_in_backup = set(current_col_names) - set(backup_col_names)
    missing_in_current = set(backup_col_names) - set(current_col_names)
    
    if missing_in_backup:
        print(f"Columns missing in backup: {missing_in_backup}")
    if missing_in_current:
        print(f"Columns missing in current: {missing_in_current}")
    
    if not missing_in_backup and not missing_in_current:
        print("✅ Schemas are compatible")

if __name__ == "__main__":
    check_schema_diff()
