#!/usr/bin/env python3
"""
Script to restore production data from the latest backup
"""

import os
import sys
import json
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash

# Load environment variables
load_dotenv()

def get_database_connection():
    """Get connection to production database"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    # Convert postgres:// to postgresql:// for psycopg2
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def load_backup_data():
    """Load the latest backup data"""
    backup_file = "backups/neon_backup_20250807_145537.json"
    
    if not os.path.exists(backup_file):
        print(f"Error: Backup file {backup_file} not found")
        sys.exit(1)
    
    try:
        with open(backup_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading backup data: {e}")
        sys.exit(1)

def clear_existing_data(conn):
    """Clear existing data from all tables"""
    cursor = conn.cursor()
    
    print("Clearing existing data...")
    
    # Clear tables in reverse dependency order
    tables = [
        'activity_log',
        'password_history', 
        'recruitment_document',
        'external_link',
        'recruitment_event',
        'university_contact',
        'cadet',
        'potential_recruit',
        'user'
    ]
    
    for table in tables:
        try:
            cursor.execute(f'DELETE FROM "{table}"')
            print(f"✓ Cleared {table}")
        except Exception as e:
            print(f"⚠ Error clearing {table}: {e}")
    
    # Reset sequences
    sequences = [
        'user_id_seq',
        'potential_recruit_id_seq', 
        'cadet_id_seq',
        'university_contact_id_seq',
        'recruitment_event_id_seq',
        'external_link_id_seq',
        'recruitment_document_id_seq',
        'password_history_id_seq',
        'activity_log_id_seq'
    ]
    
    for seq in sequences:
        try:
            cursor.execute(f'ALTER SEQUENCE "{seq}" RESTART WITH 1')
            print(f"✓ Reset sequence {seq}")
        except Exception as e:
            print(f"⚠ Error resetting {seq}: {e}")
    
    conn.commit()
    cursor.close()

def restore_users(conn, users_data):
    """Restore users data"""
    cursor = conn.cursor()
    
    print(f"Restoring {len(users_data)} users...")
    
    for user in users_data:
        try:
            # Map old field names to new schema
            cursor.execute("""
                INSERT INTO "user" (
                    id, username, email, password_hash, first_name, last_name,
                    phone, role, is_active, is_locked, failed_login_attempts,
                    password_changed_at, password_expires_at, force_password_change,
                    secret_question, secret_answer_hash, totp_secret, totp_enabled,
                    backup_codes_hash, totp_setup_completed, can_enable_2fa,
                    created_at, last_modified
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                user.get('id'),
                user.get('username'),
                user.get('email'),
                user.get('password_hash'),
                user.get('first_name'),
                user.get('last_name'),
                user.get('phone'),
                user.get('role', 'recruiter'),
                user.get('is_active', True),
                user.get('is_locked', False),
                user.get('failed_login_attempts', 0),
                user.get('password_changed_at'),
                user.get('password_expires_at'),
                user.get('force_password_change', False),
                user.get('secret_question'),
                user.get('secret_answer_hash'),
                user.get('totp_secret'),
                user.get('totp_enabled', False),
                user.get('backup_codes_hash'),
                user.get('totp_setup_completed', False),
                user.get('can_enable_2fa', True),
                user.get('created_at'),
                user.get('last_modified')
            ))
            print(f"✓ Restored user: {user.get('username')}")
        except Exception as e:
            print(f"⚠ Error restoring user {user.get('username')}: {e}")
    
    conn.commit()
    cursor.close()

def restore_cadets(conn, cadets_data):
    """Restore cadets data"""
    cursor = conn.cursor()
    
    print(f"Restoring {len(cadets_data)} cadets...")
    
    for cadet in cadets_data:
        try:
            cursor.execute("""
                INSERT INTO cadet (
                    id, first_name, last_name, email, phone, major, graduation_year,
                    cadet_rank, hometown, officer_interest, status, unenrollment_reason,
                    unenrollment_date, gpa, created_at, last_modified
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                cadet.get('id'),
                cadet.get('first_name'),
                cadet.get('last_name'),
                cadet.get('email'),
                cadet.get('phone'),
                cadet.get('major'),
                cadet.get('class_year'),  # Map class_year to graduation_year
                cadet.get('rank'),  # Map rank to cadet_rank
                cadet.get('hometown'),
                cadet.get('officer_interest'),
                cadet.get('status'),
                cadet.get('unenrollment_reason'),
                cadet.get('unenrollment_date'),
                cadet.get('gpa'),
                cadet.get('created_at'),
                cadet.get('updated_at') or cadet.get('created_at')  # Map updated_at to last_modified
            ))
            print(f"✓ Restored cadet: {cadet.get('first_name')} {cadet.get('last_name')}")
        except Exception as e:
            print(f"⚠ Error restoring cadet {cadet.get('first_name')} {cadet.get('last_name')}: {e}")
    
    conn.commit()
    cursor.close()

def restore_potential_recruits(conn, recruits_data):
    """Restore potential recruits data"""
    cursor = conn.cursor()
    
    print(f"Restoring {len(recruits_data)} potential recruits...")
    
    for recruit in recruits_data:
        try:
            cursor.execute("""
                INSERT INTO potential_recruit (
                    id, first_name, last_name, email, phone, major, current_school,
                    school_type, high_school_graduation_year, expected_college_graduation_year,
                    gpa, sat_score, act_score, interests, notes, status, created_at, last_modified
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                recruit.get('id'),
                recruit.get('first_name'),
                recruit.get('last_name'),
                recruit.get('email'),
                recruit.get('phone'),
                recruit.get('major'),
                recruit.get('current_school'),
                recruit.get('school_type'),
                recruit.get('high_school_graduation_year'),
                recruit.get('expected_college_graduation_year'),
                recruit.get('gpa'),
                recruit.get('sat_score'),
                recruit.get('act_score'),
                recruit.get('interests'),
                recruit.get('notes'),
                recruit.get('status', 'prospective'),
                recruit.get('created_at'),
                recruit.get('updated_at') or recruit.get('created_at')
            ))
            print(f"✓ Restored recruit: {recruit.get('first_name')} {recruit.get('last_name')}")
        except Exception as e:
            print(f"⚠ Error restoring recruit {recruit.get('first_name')} {recruit.get('last_name')}: {e}")
    
    conn.commit()
    cursor.close()

def restore_other_tables(conn, backup_data):
    """Restore other tables (contacts, events, etc.)"""
    cursor = conn.cursor()
    
    # Restore university contacts
    if 'university_contact' in backup_data['tables']:
        contacts_data = backup_data['tables']['university_contact']['data']
        print(f"Restoring {len(contacts_data)} university contacts...")
        
        for contact in contacts_data:
            try:
                cursor.execute("""
                    INSERT INTO university_contact (
                        id, university_name, contact_name, contact_title, email,
                        phone, address, notes, is_active, created_at, last_modified
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    contact.get('id'),
                    contact.get('university_name'),
                    contact.get('contact_name'),
                    contact.get('contact_title'),
                    contact.get('email'),
                    contact.get('phone'),
                    contact.get('address'),
                    contact.get('notes'),
                    contact.get('is_active', True),
                    contact.get('created_at'),
                    contact.get('updated_at') or contact.get('created_at')
                ))
                print(f"✓ Restored contact: {contact.get('contact_name')}")
            except Exception as e:
                print(f"⚠ Error restoring contact {contact.get('contact_name')}: {e}")
    
    # Restore recruitment events
    if 'recruitment_event' in backup_data['tables']:
        events_data = backup_data['tables']['recruitment_event']['data']
        print(f"Restoring {len(events_data)} recruitment events...")
        
        for event in events_data:
            try:
                cursor.execute("""
                    INSERT INTO recruitment_event (
                        id, title, description, event_date, start_time, end_time,
                        location, university_id, event_type, status, attendees_count,
                        notes, created_at, last_modified
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    event.get('id'),
                    event.get('title'),
                    event.get('description'),
                    event.get('event_date'),
                    event.get('start_time'),
                    event.get('end_time'),
                    event.get('location'),
                    event.get('university_id'),
                    event.get('event_type'),
                    event.get('status', 'scheduled'),
                    event.get('attendees_count', 0),
                    event.get('notes'),
                    event.get('created_at'),
                    event.get('updated_at') or event.get('created_at')
                ))
                print(f"✓ Restored event: {event.get('title')}")
            except Exception as e:
                print(f"⚠ Error restoring event {event.get('title')}: {e}")
    
    conn.commit()
    cursor.close()

def main():
    print("=== Production Data Restore ===")
    
    # Load backup data
    print("Loading backup data...")
    backup_data = load_backup_data()
    print(f"✓ Loaded backup from {backup_data['metadata']['backup_timestamp']}")
    print(f"✓ Total records: {backup_data['metadata']['total_records']}")
    
    # Connect to database
    conn = get_database_connection()
    print("✓ Connected to production database")
    
    # Clear existing data
    clear_existing_data(conn)
    
    # Restore data in dependency order
    if 'user' in backup_data['tables']:
        restore_users(conn, backup_data['tables']['user']['data'])
    
    if 'potential_recruit' in backup_data['tables']:
        restore_potential_recruits(conn, backup_data['tables']['potential_recruit']['data'])
    
    if 'cadet' in backup_data['tables']:
        restore_cadets(conn, backup_data['tables']['cadet']['data'])
    
    # Restore other tables
    restore_other_tables(conn, backup_data)
    
    conn.close()
    print("\n=== Data restore complete ===")
    print("You can now log in to production with your existing credentials!")

if __name__ == "__main__":
    main()
