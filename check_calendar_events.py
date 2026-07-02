#!/usr/bin/env python3
"""
Script to check current calendar events and their details
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

def check_calendar_events(conn):
    """Check current calendar events"""
    cursor = conn.cursor()
    
    print("=== CALENDAR EVENTS ANALYSIS ===")
    print()
    
    # Get all recruitment events
    cursor.execute("""
        SELECT 
            re.id,
            re.title,
            re.description,
            re.event_date,
            re.start_time,
            re.end_time,
            re.location,
            re.event_type,
            re.status,
            re.attendees_count,
            re.notes,
            uc.university_name as school_name
        FROM recruitment_event re
        LEFT JOIN university_contact uc ON re.university_id = uc.id
        ORDER BY re.event_date, re.start_time
    """)
    
    events = cursor.fetchall()
    
    print(f"Total calendar events: {len(events)}")
    print()
    
    if events:
        print("Current Events:")
        print("-" * 80)
        for event in events:
            event_id, title, description, event_date, start_time, end_time, location, event_type, status, attendees_count, notes, school_name = event
            
            print(f"ID: {event_id}")
            print(f"Title: {title}")
            print(f"Date: {event_date}")
            if start_time:
                print(f"Time: {start_time} - {end_time if end_time else 'TBD'}")
            print(f"Location: {location}")
            print(f"School: {school_name if school_name else 'Not assigned'}")
            print(f"Type: {event_type}")
            print(f"Status: {status}")
            print(f"Attendees: {attendees_count}")
            if description:
                print(f"Description: {description[:100]}{'...' if len(description) > 100 else ''}")
            if notes:
                print(f"Notes: {notes[:100]}{'...' if len(notes) > 100 else ''}")
            print("-" * 80)
    else:
        print("No calendar events found!")
    
    # Check events by month
    print()
    print("Events by Month:")
    print("-" * 40)
    cursor.execute("""
        SELECT 
            EXTRACT(MONTH FROM event_date) as month,
            EXTRACT(YEAR FROM event_date) as year,
            COUNT(*) as event_count
        FROM recruitment_event
        GROUP BY EXTRACT(MONTH FROM event_date), EXTRACT(YEAR FROM event_date)
        ORDER BY year, month
    """)
    
    monthly_events = cursor.fetchall()
    for month, year, count in monthly_events:
        month_name = datetime(int(year), int(month), 1).strftime('%B')
        print(f"{month_name} {year}: {count} events")
    
    # Check events by school
    print()
    print("Events by School:")
    print("-" * 40)
    cursor.execute("""
        SELECT 
            uc.university_name,
            COUNT(re.id) as event_count
        FROM university_contact uc
        LEFT JOIN recruitment_event re ON uc.id = re.university_id
        GROUP BY uc.university_name
        ORDER BY event_count DESC, uc.university_name
    """)
    
    school_events = cursor.fetchall()
    for school_name, count in school_events:
        print(f"{school_name}: {count} events")
    
    cursor.close()
    
    return events

def main():
    print("=== Calendar Events Check ===")
    
    # Connect to database
    conn = get_database_connection()
    print("✓ Connected to production database")
    print()
    
    # Check calendar events
    events = check_calendar_events(conn)
    
    conn.close()
    
    print()
    print("=== SUMMARY ===")
    print(f"Total events: {len(events)}")
    
    if len(events) < 13:
        print()
        print("⚠️  ISSUE: Not enough events!")
        print(f"   Expected: At least 13 events (one per school)")
        print(f"   Found: {len(events)} events")
        print("   Need to create events for each high school")

if __name__ == "__main__":
    main()
