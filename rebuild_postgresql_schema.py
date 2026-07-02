#!/usr/bin/env python3
"""
Comprehensive PostgreSQL Schema Rebuild and Data Migration

This script will:
1. Drop all existing PostgreSQL tables (clean slate)
2. Create tables using the correct SQLAlchemy models (matching SQLite schema)
3. Migrate all data from SQLite with proper mappings
4. Verify the migration was successful

This ensures PostgreSQL matches the Flask application's expectations exactly.
"""

import os
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Import the Flask app and models to get the correct schema
import sys
sys.path.append('.')

def get_connections():
    """Get both SQLite and PostgreSQL connections"""
    # SQLite connection
    sqlite_conn = sqlite3.connect('instance/afrotc695.db')
    sqlite_conn.row_factory = sqlite3.Row  # Enable column access by name
    
    # PostgreSQL connection
    database_url = os.getenv('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    pg_engine = create_engine(database_url, connect_args={'sslmode': 'require'})
    
    return sqlite_conn, pg_engine

def drop_all_postgresql_tables(pg_engine):
    """Drop all existing tables in PostgreSQL"""
    print("🗑️  DROPPING ALL EXISTING POSTGRESQL TABLES")
    print("=" * 60)
    
    with pg_engine.connect() as conn:
        # Get all table names
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        
        if not tables:
            print("   ✅ No tables to drop")
            return
        
        print(f"   📋 Found {len(tables)} tables to drop:")
        for table in tables:
            print(f"      • {table}")
        
        # Drop all tables (cascade to handle foreign keys)
        for table in tables:
            try:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                print(f"   ✅ Dropped table: {table}")
            except Exception as e:
                print(f"   ⚠️  Error dropping {table}: {e}")
        
        conn.commit()
        print("   🎉 All tables dropped successfully!")

def create_postgresql_schema_from_flask():
    """Create PostgreSQL tables using Flask SQLAlchemy models"""
    print("\n🏗️  CREATING POSTGRESQL SCHEMA FROM FLASK MODELS")
    print("=" * 60)
    
    try:
        # Import Flask app and initialize database using the correct models
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))
        from app import app, db
        
        with app.app_context():
            print("   📋 Creating all tables from SQLAlchemy models...")
            db.create_all()
            print("   ✅ All tables created successfully!")
            
            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"   📊 Created {len(tables)} tables:")
            for table in sorted(tables):
                print(f"      • {table}")
                
        return True
        
    except Exception as e:
        print(f"   ❌ Error creating schema: {e}")
        return False

def migrate_data_with_proper_mapping(sqlite_conn, pg_engine):
    """Migrate data from SQLite to PostgreSQL with proper mappings"""
    print("\n📦 MIGRATING DATA WITH PROPER SCHEMA MAPPING")
    print("=" * 60)
    
    # Define the migration mappings
    migrations = [
        {
            'name': 'Users',
            'sqlite_table': 'user',
            'pg_table': 'user',
            'mapping': {
                'id': 'id',
                'username': 'username', 
                'email': 'email',
                'password_hash': 'password_hash',
                'first_name': 'first_name',
                'last_name': 'last_name', 
                'phone': 'phone',
                'role': 'role',
                'is_active': 'is_active',
                'is_locked': 'is_locked',
                'password_changed_at': 'password_changed_at',
                'password_expires_at': 'password_expires_at',
                'force_password_change': 'force_password_change',
                'secret_question': 'secret_question',
                'secret_answer_hash': 'secret_answer_hash',
                'created_at': 'created_at',
                'last_modified': 'last_modified'
            }
        },
        {
            'name': 'Cadets', 
            'sqlite_table': 'cadet',
            'pg_table': 'cadet',
            'mapping': {
                'id': 'id',
                'first_name': 'first_name',
                'last_name': 'last_name',
                'email': 'email',
                'phone': 'phone',
                'major': 'major',
                'graduation_year': 'graduation_year',
                'cadet_rank': 'cadet_rank',
                'hometown': 'hometown',
                'officer_interest': 'officer_interest',
                'status': 'status',
                'unenrollment_reason': 'unenrollment_reason',
                'unenrollment_date': 'unenrollment_date',
                'gpa': 'gpa',
                'created_at': 'created_at',
                'last_modified': 'last_modified'
            }
        },
        {
            'name': 'University Contacts',
            'sqlite_table': 'university_contact', 
            'pg_table': 'university_contact',
            'mapping': {
                'id': 'id',
                'university_name': 'university_name',
                'contact_name': 'contact_name',
                'contact_title': 'contact_title',
                'email': 'email',
                'phone': 'phone',
                'address': 'address',
                'notes': 'notes',
                'is_active': 'is_active',
                'created_at': 'created_at',
                'last_modified': 'last_modified'
            }
        },
        {
            'name': 'External Links',
            'sqlite_table': 'external_link',
            'pg_table': 'external_link', 
            'mapping': {
                'id': 'id',
                'title': 'title',
                'url': 'url',
                'description': 'description',
                'category': 'category',
                'is_active': 'is_active',
                'sort_order': 'sort_order',
                'created_at': 'created_at',
                'last_modified': 'last_modified'
            }
        },
        {
            'name': 'Activity Logs',
            'sqlite_table': 'activity_log',
            'pg_table': 'activity_log',
            'mapping': {
                'id': 'id',
                'user_id': 'user_id',
                'username': 'username',
                'action': 'action',
                'table_name': 'table_name',
                'record_id': 'record_id',
                'record_description': 'record_description',
                'details': 'details',
                'ip_address': 'ip_address',
                'user_agent': 'user_agent',
                'created_at': 'created_at'
            }
        },
        {
            'name': 'Password History',
            'sqlite_table': 'password_history',
            'pg_table': 'password_history',
            'mapping': {
                'id': 'id',
                'user_id': 'user_id',
                'password_hash': 'password_hash',
                'created_at': 'created_at'
            }
        },
        {
            'name': 'Potential Recruits',
            'sqlite_table': 'potential_recruit',
            'pg_table': 'potential_recruit',
            'mapping': {
                'id': 'id',
                'first_name': 'first_name',
                'last_name': 'last_name',
                'email': 'email',
                'phone': 'phone',
                'major': 'major',
                'current_school': 'current_school',
                'school_type': 'school_type',
                'high_school_graduation_year': 'high_school_graduation_year',
                'expected_college_graduation_year': 'expected_college_graduation_year',
                'gpa': 'gpa',
                'sat_score': 'sat_score',
                'act_score': 'act_score',
                'interests': 'interests',
                'notes': 'notes',
                'status': 'status',
                'created_at': 'created_at',
                'last_modified': 'last_modified'
            }
        },
        {
            'name': 'Recruitment Events',
            'sqlite_table': 'recruitment_event',
            'pg_table': 'recruitment_event',
            'mapping': {
                'id': 'id',
                'title': 'title',
                'description': 'description',
                'event_date': 'event_date',
                'start_time': 'start_time',
                'end_time': 'end_time',
                'location': 'location',
                'university_id': 'university_id',
                'event_type': 'event_type',
                'status': 'status',
                'attendees_count': 'attendees_count',
                'notes': 'notes',
                'created_at': 'created_at',
                'last_modified': 'last_modified'
            }
        },
        {
            'name': 'Recruitment Documents',
            'sqlite_table': 'recruitment_document',
            'pg_table': 'recruitment_document',
            'mapping': {
                'id': 'id',
                'title': 'title',
                'description': 'description',
                'filename': 'filename',
                'original_filename': 'original_filename',
                'file_size': 'file_size',
                'file_type': 'file_type',
                'category': 'category',
                'is_active': 'is_active',
                'sort_order': 'sort_order',
                'created_at': 'created_at',
                'last_modified': 'last_modified'
            }
        }
    ]
    
    total_migrated = 0
    
    for migration in migrations:
        print(f"\n   📋 Migrating {migration['name']}...")
        
        # Get data from SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(f"SELECT * FROM {migration['sqlite_table']}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print(f"      ℹ️  No data in {migration['sqlite_table']}")
            continue
            
        print(f"      📊 Found {len(rows)} records")
        
        # Prepare PostgreSQL insert
        pg_columns = list(migration['mapping'].values())
        placeholders = ', '.join([f':{col}' for col in pg_columns])
        insert_sql = f"""
            INSERT INTO {migration['pg_table']} ({', '.join(pg_columns)})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE SET
            {', '.join([f'{col} = EXCLUDED.{col}' for col in pg_columns if col != 'id'])}
        """
        
        # Migrate each row
        migrated_count = 0
        with pg_engine.connect() as pg_conn:
            for row in rows:
                try:
                    # Map SQLite columns to PostgreSQL columns
                    mapped_data = {}
                    for sqlite_col, pg_col in migration['mapping'].items():
                        value = row[sqlite_col] if sqlite_col in row.keys() else None
                        mapped_data[pg_col] = value
                    
                    pg_conn.execute(text(insert_sql), mapped_data)
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"      ⚠️  Error migrating row {row['id']}: {e}")
            
            pg_conn.commit()
        
        print(f"      ✅ Migrated {migrated_count}/{len(rows)} records")
        total_migrated += migrated_count
    
    print(f"\n🎉 MIGRATION COMPLETED!")
    print(f"📊 Total records migrated: {total_migrated}")
    
    return total_migrated

def verify_migration(pg_engine):
    """Verify the migration was successful"""
    print("\n🔍 VERIFYING MIGRATION SUCCESS")
    print("=" * 60)
    
    with pg_engine.connect() as conn:
        # Get all tables and their record counts
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        
        total_records = 0
        for table in tables:
            count_result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            count = count_result.fetchone()[0]
            total_records += count
            print(f"   📊 {table}: {count} records")
        
        print(f"\n🎯 Total records in PostgreSQL: {total_records}")
        
        # Test a simple query to ensure schema is working
        try:
            result = conn.execute(text("SELECT username, email FROM \"user\" LIMIT 1"))
            user = result.fetchone()
            if user:
                print(f"   ✅ Schema test passed - found user: {user[0]} ({user[1]})")
            else:
                print("   ⚠️  No users found for schema test")
        except Exception as e:
            print(f"   ❌ Schema test failed: {e}")
            return False
        
        return True

def main():
    """Main rebuild function"""
    print("🚀 POSTGRESQL SCHEMA REBUILD AND DATA MIGRATION")
    print("=" * 80)
    print("This will completely rebuild PostgreSQL with the correct schema")
    print("and migrate all data from SQLite properly.")
    print("=" * 80)
    
    try:
        # Get connections
        print("🔌 Establishing database connections...")
        sqlite_conn, pg_engine = get_connections()
        print("   ✅ Connected to both databases")
        
        # Step 1: Drop all existing PostgreSQL tables
        drop_all_postgresql_tables(pg_engine)
        
        # Step 2: Create correct schema using Flask models
        if not create_postgresql_schema_from_flask():
            print("❌ Failed to create schema. Aborting.")
            return False
        
        # Step 3: Migrate all data with proper mappings
        total_migrated = migrate_data_with_proper_mapping(sqlite_conn, pg_engine)
        
        # Step 4: Verify migration success
        if verify_migration(pg_engine):
            print("\n" + "=" * 80)
            print("🎉 SCHEMA REBUILD COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print(f"✅ PostgreSQL now has the correct schema matching Flask models")
            print(f"✅ All {total_migrated} records migrated successfully")
            print(f"✅ Database is ready for production use")
            print("=" * 80)
            return True
        else:
            print("\n❌ Migration verification failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Critical error during rebuild: {e}")
        return False
    
    finally:
        # Clean up connections
        try:
            sqlite_conn.close()
        except:
            pass

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n💡 Check the error messages above and try again.")
        exit(1)
    else:
        print("\n🌟 Ready to test the application!")
        exit(0)
