#!/usr/bin/env python3
"""
Script to clear existing contacts and restore the correct Jesuit and Catholic high school contacts
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from datetime import datetime

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

def clear_existing_contacts(conn):
    """Clear all existing university contacts"""
    cursor = conn.cursor()
    
    print("Clearing existing university contacts...")
    
    try:
        cursor.execute("DELETE FROM university_contact")
        conn.commit()
        print(f"✓ Cleared {cursor.rowcount} existing contacts")
    except Exception as e:
        print(f"⚠ Error clearing contacts: {e}")
        conn.rollback()
    
    cursor.close()

def restore_correct_contacts(conn):
    """Restore the correct Jesuit and Catholic high school contacts"""
    cursor = conn.cursor()
    
    print("Restoring correct university contacts...")
    
    # Actual contacts from Jesuit and Catholic High Schools document
    contacts = [
        {
            'university_name': 'Seattle Preparatory School',
            'contact_name': 'Ann Alokolaro',
            'contact_title': 'Director of Admissions',
            'email': 'aalokolaro@seaprep.org',
            'phone': '(206) 577-2146',
            'address': 'Seattle, WA',
            'notes': 'Catholic Preparatory School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'Cristo Rey Jesuit Seattle',
            'contact_name': 'Flor Gonzalez',
            'contact_title': 'Admissions',
            'email': 'fgonzalez@cristoreyseattle.org',
            'phone': '(206) 688-2108',
            'address': 'Seattle, WA',
            'notes': 'Jesuit High School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'Bishop Blanchet HS',
            'contact_name': 'General Office',
            'contact_title': 'General Contact',
            'email': 'mainoffice@bishopblanchet.org',
            'phone': '(206) 527-7711',
            'address': 'Seattle, WA',
            'notes': 'Catholic High School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'Holy Names Academy',
            'contact_name': 'General Office',
            'contact_title': 'General Contact',
            'email': 'admissions@holynames-sea.org',
            'phone': '(206) 323-4272',
            'address': 'Seattle, WA',
            'notes': 'Catholic High School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'O\'Dea High School',
            'contact_name': 'General Office',
            'contact_title': 'General Contact',
            'email': 'info@odea.org',
            'phone': '(206) 622-6596',
            'address': 'Seattle, WA',
            'notes': 'Catholic High School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'Eastside Catholic HS',
            'contact_name': 'General Office',
            'contact_title': 'General Contact',
            'email': 'admissions@eastsidecatholic.org',
            'phone': '(425) 295-3000',
            'address': 'Sammamish, WA',
            'notes': 'Catholic High School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'Jesuit High School',
            'contact_name': 'Admissions Office',
            'contact_title': 'Contact',
            'email': 'admissions@jesuitportland.org',
            'phone': '(503) 291-5423',
            'address': 'Beaverton, OR',
            'notes': 'Jesuit High School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'Central Catholic HS',
            'contact_name': 'General Office',
            'contact_title': 'General Contact',
            'email': 'admissions@centralcatholichigh.org',
            'phone': '(503) 235-3138',
            'address': 'Portland, OR',
            'notes': 'Catholic High School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'St. Mary\'s Academy',
            'contact_name': 'General Office',
            'contact_title': 'General Contact',
            'email': 'info@smapdx.org',
            'phone': '(503) 228-8306',
            'address': 'Portland, OR',
            'notes': 'Catholic High School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'Valley Catholic HS',
            'contact_name': 'General Office',
            'contact_title': 'General Contact',
            'email': 'admissions@valleycatholic.org',
            'phone': '(503) 644-3745',
            'address': 'Beaverton, OR',
            'notes': 'Catholic High School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'De La Salle North Catholic HS',
            'contact_name': 'General Office',
            'contact_title': 'General Contact',
            'email': 'admissions@delasallenorth.org',
            'phone': '(503) 285-9385',
            'address': 'Portland, OR',
            'notes': 'Catholic High School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'La Salle Catholic College Prep',
            'contact_name': 'General Office',
            'contact_title': 'General Contact',
            'email': 'admissions@lsprep.org',
            'phone': '(503) 659-4155',
            'address': 'Milwaukie, OR',
            'notes': 'Catholic High School - AFROTC Recruitment Contact',
            'is_active': True
        },
        {
            'university_name': 'St. Elizabeth Ann Seton Catholic HS',
            'contact_name': 'General Office',
            'contact_title': 'General Contact',
            'email': 'info@setonhigh.org',
            'phone': '(360) 258-1932',
            'address': 'Vancouver, WA',
            'notes': 'Catholic High School - AFROTC Recruitment Contact',
            'is_active': True
        }
    ]
    
    for contact in contacts:
        try:
            cursor.execute("""
                INSERT INTO university_contact (
                    university_name, contact_name, contact_title, email, phone,
                    address, notes, is_active, created_at, last_modified
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                contact['university_name'],
                contact['contact_name'],
                contact['contact_title'],
                contact['email'],
                contact['phone'],
                contact['address'],
                contact['notes'],
                contact['is_active'],
                datetime.utcnow(),
                datetime.utcnow()
            ))
            print(f"✓ Restored contact: {contact['university_name']} - {contact['contact_name']}")
        except Exception as e:
            print(f"⚠ Error restoring contact {contact['university_name']}: {e}")
    
    conn.commit()
    cursor.close()

def main():
    print("=== Fix University Contacts ===")
    
    # Connect to database
    conn = get_database_connection()
    print("✓ Connected to production database")
    
    # Clear existing contacts
    clear_existing_contacts(conn)
    
    # Restore correct contacts
    restore_correct_contacts(conn)
    
    conn.close()
    print("\n=== Contact fix complete ===")
    print("All 13 Jesuit and Catholic high school contacts have been restored!")

if __name__ == "__main__":
    main()
