#!/usr/bin/env python3
"""
Script to inspect and compare SQLite and PostgreSQL schemas
"""

import sqlite3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

load_dotenv()

def inspect_sqlite_schema():
    """Inspect SQLite database schema"""
    print("🔍 SQLite Database Schema:")
    print("=" * 40)
    
    conn = sqlite3.connect("instance/afrotc695.db")
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']
    
    for table in tables:
        print(f"\n📋 Table: {table}")
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        for col in columns:
            col_id, name, type_name, not_null, default, pk = col
            pk_marker = " (PK)" if pk else ""
            print(f"  • {name} ({type_name}){pk_marker}")
    
    conn.close()
    return tables

def inspect_postgresql_schema():
    """Inspect PostgreSQL database schema"""
    print("\n🔍 PostgreSQL Database Schema:")
    print("=" * 40)
    
    database_url = os.getenv('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url, connect_args={"sslmode": "require"})
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    for table in tables:
        print(f"\n📋 Table: {table}")
        columns = inspector.get_columns(table)
        for col in columns:
            pk_marker = " (PK)" if col.get('primary_key') else ""
            nullable = "" if col['nullable'] else " NOT NULL"
            print(f"  • {col['name']} ({col['type']}){pk_marker}{nullable}")
    
    return tables

def main():
    print("🔍 DATABASE SCHEMA COMPARISON")
    print("=" * 50)
    
    sqlite_tables = inspect_sqlite_schema()
    postgres_tables = inspect_postgresql_schema()
    
    print("\n📊 COMPARISON SUMMARY:")
    print("=" * 30)
    print(f"SQLite tables: {len(sqlite_tables)}")
    print(f"PostgreSQL tables: {len(postgres_tables)}")
    
    common_tables = set(sqlite_tables) & set(postgres_tables)
    sqlite_only = set(sqlite_tables) - set(postgres_tables)
    postgres_only = set(postgres_tables) - set(sqlite_tables)
    
    if common_tables:
        print(f"\n✅ Common tables: {list(common_tables)}")
    if sqlite_only:
        print(f"📤 SQLite only: {list(sqlite_only)}")
    if postgres_only:
        print(f"📥 PostgreSQL only: {list(postgres_only)}")

if __name__ == "__main__":
    main()
