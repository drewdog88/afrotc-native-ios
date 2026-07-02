#!/usr/bin/env python3
"""
Comprehensive analysis of schema differences between SQLite and PostgreSQL
"""

import sqlite3
from sqlalchemy import create_engine, text, inspect
import os
from dotenv import load_dotenv

load_dotenv()

def analyze_sqlite_schema():
    """Analyze the original SQLite database schema"""
    print("🔍 ANALYZING ORIGINAL SQLITE DATABASE")
    print("=" * 60)
    
    sqlite_path = "instance/afrotc695.db"
    if not os.path.exists(sqlite_path):
        print(f"❌ SQLite database not found at {sqlite_path}")
        return {}
    
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()
    
    sqlite_schema = {}
    
    for (table_name,) in tables:
        print(f"\n📋 Table: {table_name}")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        table_info = []
        for col in columns:
            cid, name, type_, notnull, default, pk = col
            table_info.append({
                'name': name,
                'type': type_,
                'nullable': not notnull,
                'primary_key': bool(pk),
                'default': default
            })
            nullable_str = "nullable" if not notnull else "NOT NULL"
            pk_str = " (PK)" if pk else ""
            print(f"   {name} - {type_} - {nullable_str}{pk_str}")
        
        sqlite_schema[table_name] = table_info
        
        # Get record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"   📊 Records: {count}")
    
    conn.close()
    return sqlite_schema

def analyze_postgresql_schema():
    """Analyze the current PostgreSQL database schema"""
    print("\n\n🐘 ANALYZING CURRENT POSTGRESQL DATABASE")
    print("=" * 60)
    
    database_url = os.getenv('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url, connect_args={'sslmode': 'require'})
    
    postgresql_schema = {}
    
    with engine.connect() as conn:
        # Get all tables
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        
        for table_name in tables:
            print(f"\n📋 Table: {table_name}")
            
            # Get column information
            result = conn.execute(text(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                ORDER BY ordinal_position
            """))
            
            table_info = []
            for row in result:
                col_name, data_type, is_nullable, default = row
                table_info.append({
                    'name': col_name,
                    'type': data_type,
                    'nullable': is_nullable == 'YES',
                    'default': default
                })
                nullable_str = "nullable" if is_nullable == 'YES' else "NOT NULL"
                print(f"   {col_name} - {data_type} - {nullable_str}")
            
            postgresql_schema[table_name] = table_info
            
            # Get record count
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            count = result.fetchone()[0]
            print(f"   📊 Records: {count}")
    
    return postgresql_schema

def compare_schemas(sqlite_schema, postgresql_schema):
    """Compare the two schemas and identify differences"""
    print("\n\n⚖️  SCHEMA COMPARISON ANALYSIS")
    print("=" * 60)
    
    all_tables = set(sqlite_schema.keys()) | set(postgresql_schema.keys())
    
    issues = []
    
    for table in sorted(all_tables):
        print(f"\n📊 Table: {table}")
        
        if table not in sqlite_schema:
            print(f"   ⚠️  Table exists only in PostgreSQL")
            issues.append(f"Table '{table}' exists only in PostgreSQL")
            continue
            
        if table not in postgresql_schema:
            print(f"   ⚠️  Table exists only in SQLite")
            issues.append(f"Table '{table}' exists only in SQLite")
            continue
        
        # Compare columns
        sqlite_cols = {col['name']: col for col in sqlite_schema[table]}
        postgresql_cols = {col['name']: col for col in postgresql_schema[table]}
        
        all_columns = set(sqlite_cols.keys()) | set(postgresql_cols.keys())
        
        for col_name in sorted(all_columns):
            if col_name not in sqlite_cols:
                print(f"   ➕ Column '{col_name}' exists only in PostgreSQL")
                issues.append(f"Table '{table}': Column '{col_name}' exists only in PostgreSQL")
            elif col_name not in postgresql_cols:
                print(f"   ➖ Column '{col_name}' exists only in SQLite")
                issues.append(f"Table '{table}': Column '{col_name}' exists only in SQLite")
            else:
                # Column exists in both, check for differences
                sqlite_col = sqlite_cols[col_name]
                postgresql_col = postgresql_cols[col_name]
                
                if sqlite_col['nullable'] != postgresql_col['nullable']:
                    print(f"   🔄 Column '{col_name}': nullable mismatch")
                    issues.append(f"Table '{table}': Column '{col_name}' nullable mismatch")
    
    return issues

def analyze_flask_models():
    """Analyze the current Flask SQLAlchemy models"""
    print("\n\n🌶️  ANALYZING FLASK SQLALCHEMY MODELS")
    print("=" * 60)
    
    # Read the api/app.py file and extract model definitions
    try:
        with open('api/app.py', 'r') as f:
            content = f.read()
        
        # Find all class definitions that inherit from db.Model
        import re
        model_pattern = r'class (\w+)\(db\.Model\):(.*?)(?=class|\Z)'
        models = re.findall(model_pattern, content, re.DOTALL)
        
        print(f"Found {len(models)} SQLAlchemy models:")
        for model_name, model_content in models:
            print(f"\n📋 Model: {model_name}")
            
            # Extract column definitions
            column_pattern = r'(\w+)\s*=\s*db\.Column\([^)]+\)'
            columns = re.findall(column_pattern, model_content)
            
            for col in columns:
                print(f"   {col}")
    
    except Exception as e:
        print(f"❌ Error analyzing Flask models: {e}")

def main():
    """Main analysis function"""
    print("🔍 COMPREHENSIVE SCHEMA ANALYSIS")
    print("=" * 80)
    print("Analyzing schema differences between SQLite source and PostgreSQL target")
    print("This will help identify ALL issues that need to be fixed.")
    print("=" * 80)
    
    # Analyze both schemas
    sqlite_schema = analyze_sqlite_schema()
    postgresql_schema = analyze_postgresql_schema()
    
    # Compare them
    issues = compare_schemas(sqlite_schema, postgresql_schema)
    
    # Analyze Flask models
    analyze_flask_models()
    
    # Summary
    print("\n\n📋 SUMMARY OF ISSUES")
    print("=" * 60)
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"{i:2d}. {issue}")
    else:
        print("✅ No schema differences found!")
    
    print(f"\n🎯 TOTAL ISSUES FOUND: {len(issues)}")
    print("\nThese issues need to be systematically addressed before the application will work correctly.")

if __name__ == "__main__":
    main()
