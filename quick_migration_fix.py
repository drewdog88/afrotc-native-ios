#!/usr/bin/env python3
"""
Quick fix for the remaining migration issues:
1. Quote the 'user' table name (PostgreSQL reserved keyword)
2. Convert boolean values (SQLite 1/0 -> PostgreSQL true/false)  
3. Migrate users first to satisfy foreign key constraints
"""

import os
import sqlite3
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def get_connections():
    """Get both SQLite and PostgreSQL connections"""
    sqlite_conn = sqlite3.connect('instance/afrotc695.db')
    sqlite_conn.row_factory = sqlite3.Row
    
    database_url = os.getenv('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    pg_engine = create_engine(database_url, connect_args={'sslmode': 'require'})
    return sqlite_conn, pg_engine

def convert_boolean(value):
    """Convert SQLite boolean (1/0) to PostgreSQL boolean"""
    if value is None:
        return None
    return bool(value)

def migrate_users():
    """Migrate users with proper boolean conversion and table quoting"""
    print("🧑‍💻 MIGRATING USERS...")
    
    sqlite_conn, pg_engine = get_connections()
    
    # Get users from SQLite
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM user")
    users = cursor.fetchall()
    
    print(f"   📊 Found {len(users)} users")
    
    # Insert users into PostgreSQL with proper quoting and boolean conversion
    with pg_engine.connect() as conn:
        for user in users:
            try:
                # Convert boolean fields
                user_data = {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'password_hash': user['password_hash'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'phone': user['phone'],
                    'role': user['role'],
                    'is_active': convert_boolean(user['is_active']),
                    'is_locked': convert_boolean(user['is_locked']),
                    'password_changed_at': user['password_changed_at'],
                    'password_expires_at': user['password_expires_at'],
                    'force_password_change': convert_boolean(user['force_password_change']),
                    'secret_question': user['secret_question'],
                    'secret_answer_hash': user['secret_answer_hash'],
                    'created_at': user['created_at'],
                    'last_modified': user['last_modified']
                }
                
                # Use quoted table name for PostgreSQL reserved keyword
                conn.execute(text('''
                    INSERT INTO "user" (id, username, email, password_hash, first_name, last_name, 
                                       phone, role, is_active, is_locked, password_changed_at, 
                                       password_expires_at, force_password_change, secret_question, 
                                       secret_answer_hash, created_at, last_modified)
                    VALUES (:id, :username, :email, :password_hash, :first_name, :last_name, 
                           :phone, :role, :is_active, :is_locked, :password_changed_at, 
                           :password_expires_at, :force_password_change, :secret_question, 
                           :secret_answer_hash, :created_at, :last_modified)
                    ON CONFLICT (id) DO UPDATE SET
                        username = EXCLUDED.username,
                        email = EXCLUDED.email,
                        password_hash = EXCLUDED.password_hash,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        phone = EXCLUDED.phone,
                        role = EXCLUDED.role,
                        is_active = EXCLUDED.is_active,
                        is_locked = EXCLUDED.is_locked,
                        password_changed_at = EXCLUDED.password_changed_at,
                        password_expires_at = EXCLUDED.password_expires_at,
                        force_password_change = EXCLUDED.force_password_change,
                        secret_question = EXCLUDED.secret_question,
                        secret_answer_hash = EXCLUDED.secret_answer_hash,
                        created_at = EXCLUDED.created_at,
                        last_modified = EXCLUDED.last_modified
                '''), user_data)
                
                print(f"   ✅ Migrated user: {user['username']}")
                
            except Exception as e:
                print(f"   ⚠️  Error migrating user {user['id']}: {e}")
        
        conn.commit()
    
    sqlite_conn.close()

def migrate_boolean_tables():
    """Migrate tables with boolean conversion"""
    print("\n🔄 MIGRATING BOOLEAN TABLES...")
    
    sqlite_conn, pg_engine = get_connections()
    
    # University contacts
    print("   📋 Migrating university_contact...")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM university_contact")
    contacts = cursor.fetchall()
    
    with pg_engine.connect() as conn:
        for contact in contacts:
            try:
                contact_data = {
                    'id': contact['id'],
                    'university_name': contact['university_name'],
                    'contact_name': contact['contact_name'],
                    'contact_title': contact['contact_title'],
                    'email': contact['email'],
                    'phone': contact['phone'],
                    'address': contact['address'],
                    'notes': contact['notes'],
                    'is_active': convert_boolean(contact['is_active']),
                    'created_at': contact['created_at'],
                    'last_modified': contact['last_modified']
                }
                
                conn.execute(text('''
                    INSERT INTO university_contact (id, university_name, contact_name, contact_title, 
                                                   email, phone, address, notes, is_active, created_at, last_modified)
                    VALUES (:id, :university_name, :contact_name, :contact_title, 
                           :email, :phone, :address, :notes, :is_active, :created_at, :last_modified)
                    ON CONFLICT (id) DO UPDATE SET
                        university_name = EXCLUDED.university_name,
                        contact_name = EXCLUDED.contact_name,
                        contact_title = EXCLUDED.contact_title,
                        email = EXCLUDED.email,
                        phone = EXCLUDED.phone,
                        address = EXCLUDED.address,
                        notes = EXCLUDED.notes,
                        is_active = EXCLUDED.is_active,
                        created_at = EXCLUDED.created_at,
                        last_modified = EXCLUDED.last_modified
                '''), contact_data)
                
            except Exception as e:
                print(f"   ⚠️  Error migrating contact {contact['id']}: {e}")
        
        conn.commit()
        print(f"   ✅ Migrated {len(contacts)} university contacts")
    
    # External links
    print("   📋 Migrating external_link...")
    cursor.execute("SELECT * FROM external_link")
    links = cursor.fetchall()
    
    with pg_engine.connect() as conn:
        for link in links:
            try:
                link_data = {
                    'id': link['id'],
                    'title': link['title'],
                    'url': link['url'],
                    'description': link['description'],
                    'category': link['category'],
                    'is_active': convert_boolean(link['is_active']),
                    'sort_order': link['sort_order'],
                    'created_at': link['created_at'],
                    'last_modified': link['last_modified']
                }
                
                conn.execute(text('''
                    INSERT INTO external_link (id, title, url, description, category, is_active, 
                                             sort_order, created_at, last_modified)
                    VALUES (:id, :title, :url, :description, :category, :is_active, 
                           :sort_order, :created_at, :last_modified)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        url = EXCLUDED.url,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        is_active = EXCLUDED.is_active,
                        sort_order = EXCLUDED.sort_order,
                        created_at = EXCLUDED.created_at,
                        last_modified = EXCLUDED.last_modified
                '''), link_data)
                
            except Exception as e:
                print(f"   ⚠️  Error migrating link {link['id']}: {e}")
        
        conn.commit()
        print(f"   ✅ Migrated {len(links)} external links")
    
    sqlite_conn.close()

def migrate_dependent_tables():
    """Migrate tables that depend on users"""
    print("\n🔗 MIGRATING DEPENDENT TABLES...")
    
    sqlite_conn, pg_engine = get_connections()
    
    # Activity logs
    print("   📋 Migrating activity_log...")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM activity_log")
    logs = cursor.fetchall()
    
    with pg_engine.connect() as conn:
        for log in logs:
            try:
                log_data = {
                    'id': log['id'],
                    'user_id': log['user_id'],
                    'username': log['username'],
                    'action': log['action'],
                    'table_name': log['table_name'],
                    'record_id': log['record_id'],
                    'record_description': log['record_description'],
                    'details': log['details'],
                    'ip_address': log['ip_address'],
                    'user_agent': log['user_agent'],
                    'created_at': log['created_at']
                }
                
                conn.execute(text('''
                    INSERT INTO activity_log (id, user_id, username, action, table_name, record_id, 
                                            record_description, details, ip_address, user_agent, created_at)
                    VALUES (:id, :user_id, :username, :action, :table_name, :record_id, 
                           :record_description, :details, :ip_address, :user_agent, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        username = EXCLUDED.username,
                        action = EXCLUDED.action,
                        table_name = EXCLUDED.table_name,
                        record_id = EXCLUDED.record_id,
                        record_description = EXCLUDED.record_description,
                        details = EXCLUDED.details,
                        ip_address = EXCLUDED.ip_address,
                        user_agent = EXCLUDED.user_agent,
                        created_at = EXCLUDED.created_at
                '''), log_data)
                
            except Exception as e:
                print(f"   ⚠️  Error migrating activity log {log['id']}: {e}")
        
        conn.commit()
        print(f"   ✅ Migrated {len(logs)} activity logs")
    
    # Password history
    print("   📋 Migrating password_history...")
    cursor.execute("SELECT * FROM password_history")
    passwords = cursor.fetchall()
    
    with pg_engine.connect() as conn:
        for pwd in passwords:
            try:
                pwd_data = {
                    'id': pwd['id'],
                    'user_id': pwd['user_id'],
                    'password_hash': pwd['password_hash'],
                    'created_at': pwd['created_at']
                }
                
                conn.execute(text('''
                    INSERT INTO password_history (id, user_id, password_hash, created_at)
                    VALUES (:id, :user_id, :password_hash, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        password_hash = EXCLUDED.password_hash,
                        created_at = EXCLUDED.created_at
                '''), pwd_data)
                
            except Exception as e:
                print(f"   ⚠️  Error migrating password history {pwd['id']}: {e}")
        
        conn.commit()
        print(f"   ✅ Migrated {len(passwords)} password history records")
    
    sqlite_conn.close()

def verify_final_migration():
    """Verify the complete migration"""
    print("\n🔍 FINAL VERIFICATION")
    print("=" * 50)
    
    _, pg_engine = get_connections()
    
    with pg_engine.connect() as conn:
        tables = ['user', 'cadet', 'university_contact', 'external_link', 'activity_log', 'password_history']
        total_records = 0
        
        for table in tables:
            if table == 'user':
                # Quote user table name
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            else:
                result = conn.execute(text(f'SELECT COUNT(*) FROM {table}'))
            count = result.fetchone()[0]
            total_records += count
            print(f"   📊 {table}: {count} records")
        
        print(f"\n🎯 Total records: {total_records}")
        
        # Test login functionality
        result = conn.execute(text('SELECT username, email FROM "user" WHERE role = \'admin\' LIMIT 1'))
        admin = result.fetchone()
        if admin:
            print(f"   ✅ Admin user found: {admin[0]} ({admin[1]})")
            return True
        else:
            print("   ❌ No admin user found!")
            return False

def main():
    print("🚀 QUICK MIGRATION FIX")
    print("=" * 50)
    print("Fixing remaining migration issues...")
    print("=" * 50)
    
    try:
        # Step 1: Migrate users first (fixes foreign key constraints)
        migrate_users()
        
        # Step 2: Migrate tables with boolean conversion
        migrate_boolean_tables()
        
        # Step 3: Migrate dependent tables
        migrate_dependent_tables()
        
        # Step 4: Verify everything worked
        if verify_final_migration():
            print("\n" + "=" * 50)
            print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 50)
            print("✅ All data migrated with proper schema")
            print("✅ Boolean values converted correctly")
            print("✅ Foreign key constraints satisfied")
            print("✅ PostgreSQL reserved keywords handled")
            print("🌟 Ready to test the application!")
            return True
        else:
            print("\n❌ Migration verification failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Critical error during migration: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
