#!/usr/bin/env python3
"""
Script to check what university contacts are currently in the database
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2

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

def check_contacts(conn):
    """Check what contacts are in the database"""
    cursor = conn.cursor()
    
    print("=== CURRENT UNIVERSITY CONTACTS IN DATABASE ===")
    print()
    
    cursor.execute("SELECT university_name, contact_name, contact_title, email, phone, address, notes FROM university_contact ORDER BY university_name")
    contacts = cursor.fetchall()
    
    if not contacts:
        print("No contacts found in database.")
    else:
        print(f"Found {len(contacts)} contacts:")
        print("-" * 80)
        
        for i, contact in enumerate(contacts, 1):
            print(f"{i}. {contact[0]}")  # university_name
            print(f"   Contact: {contact[1]} ({contact[2]})")  # contact_name, contact_title
            print(f"   Email: {contact[3]}")  # email
            print(f"   Phone: {contact[4]}")  # phone
            print(f"   Address: {contact[5]}")  # address
            print(f"   Notes: {contact[6]}")  # notes
            print()
    
    cursor.close()

def main():
    print("=== Check University Contacts ===")
    
    # Connect to database
    conn = get_database_connection()
    print("✓ Connected to production database")
    
    # Check existing contacts
    check_contacts(conn)
    
    conn.close()

if __name__ == "__main__":
    main()
