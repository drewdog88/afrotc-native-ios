#!/usr/bin/env python3
"""
Test script to verify data migration without actually modifying production
"""

import sqlite3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

load_dotenv()

def test_connections():
    """Test both SQLite and Neon connections"""
    print("🔍 Testing database connections...")
    
    # Test SQLite
    sqlite_path = "instance/afrotc695.db"
    if os.path.exists(sqlite_path):
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user")
        user_count = cursor.fetchone()[0]
        conn.close()
        print(f"✅ SQLite: {user_count} users found")
    else:
        print("❌ SQLite database not found")
        return False
    
    # Test Neon PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        engine = create_engine(
            database_url,
            connect_args={"sslmode": "require"} if 'postgresql' in database_url else {}
        )
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Neon PostgreSQL connected: {version[:30]}...")
            
            # Check if tables exist
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"✅ Found {len(tables)} tables in Neon: {tables}")
            
            return True
    except Exception as e:
        print(f"❌ Neon connection failed: {e}")
        return False

def compare_schemas():
    """Compare SQLite and PostgreSQL table schemas"""
    print("\n🔍 Comparing database schemas...")
    
    # Get SQLite schema
    sqlite_conn = sqlite3.connect("instance/afrotc695.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    sqlite_tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']
    sqlite_conn.close()
    
    # Get PostgreSQL schema
    database_url = os.getenv('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(
        database_url,
        connect_args={"sslmode": "require"} if 'postgresql' in database_url else {}
    )
    inspector = inspect(engine)
    postgres_tables = inspector.get_table_names()
    
    print(f"SQLite tables ({len(sqlite_tables)}): {sqlite_tables}")
    print(f"PostgreSQL tables ({len(postgres_tables)}): {postgres_tables}")
    
    # Find missing tables
    missing_in_postgres = set(sqlite_tables) - set(postgres_tables)
    extra_in_postgres = set(postgres_tables) - set(sqlite_tables)
    
    if missing_in_postgres:
        print(f"⚠️  Tables missing in PostgreSQL: {missing_in_postgres}")
    if extra_in_postgres:
        print(f"ℹ️  Extra tables in PostgreSQL: {extra_in_postgres}")
    
    if not missing_in_postgres:
        print("✅ All SQLite tables exist in PostgreSQL")
        return True
    else:
        print("❌ Schema mismatch detected")
        return False

if __name__ == "__main__":
    print("🧪 MIGRATION TEST")
    print("=" * 50)
    
    connections_ok = test_connections()
    if connections_ok:
        schema_ok = compare_schemas()
        
        if schema_ok:
            print("\n✅ READY FOR MIGRATION!")
            print("Run 'python migrate_to_neon.py' to perform the actual migration.")
        else:
            print("\n❌ SCHEMA ISSUES DETECTED!")
            print("The database schema needs to be initialized first.")
            print("Make sure the Flask app has run at least once to create tables.")
    else:
        print("\n❌ CONNECTION ISSUES!")
        print("Fix connection problems before attempting migration.")
