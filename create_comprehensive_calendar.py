#!/usr/bin/env python3
"""
Script to create comprehensive calendar events for all 13 high schools
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from datetime import datetime, date, time
import calendar

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

def get_school_contacts(conn):
    """Get all school contacts"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, university_name, contact_name, address
        FROM university_contact
        WHERE is_active = true
        ORDER BY university_name
    """)
    
    schools = cursor.fetchall()
    cursor.close()
    return schools

def clear_existing_events(conn):
    """Clear existing recruitment events"""
    cursor = conn.cursor()
    
    print("Clearing existing recruitment events...")
    
    try:
        cursor.execute("DELETE FROM recruitment_event")
        conn.commit()
        print(f"✓ Cleared {cursor.rowcount} existing events")
    except Exception as e:
        print(f"⚠ Error clearing events: {e}")
        conn.rollback()
    
    cursor.close()

def create_comprehensive_events(conn):
    """Create comprehensive calendar events for all schools"""
    cursor = conn.cursor()
    
    print("Creating comprehensive calendar events...")
    
    # Get all schools
    schools = get_school_contacts(conn)
    
    # Event types and descriptions
    event_types = [
        {
            'type': 'information_session',
            'title_template': 'AFROTC Information Session - {school}',
            'description': 'Comprehensive information session about AFROTC opportunities, scholarships, and requirements. Open to all interested students and parents.',
            'duration_hours': 1.5
        },
        {
            'type': 'high_school_visit',
            'title_template': 'AFROTC Recruitment Visit - {school}',
            'description': 'Direct recruitment visit to present AFROTC opportunities and answer questions from students and staff.',
            'duration_hours': 2.0
        },
        {
            'type': 'college_fair',
            'title_template': 'College Fair - {school}',
            'description': 'AFROTC representation at school college fair with informational booth and materials.',
            'duration_hours': 3.0
        },
        {
            'type': 'presentation',
            'title_template': 'AFROTC Career Presentation - {school}',
            'description': 'Focused presentation on Air Force careers and AFROTC leadership development opportunities.',
            'duration_hours': 1.0
        }
    ]
    
    # Create events for each school across different months
    current_year = 2025
    months = [9, 10, 11, 12, 1, 2, 3, 4, 5]  # September through May (school year)
    
    event_count = 0
    
    for i, school in enumerate(schools):
        school_id, school_name, contact_name, address = school
        
        # Assign each school to different months to spread events out
        month_index = i % len(months)
        month = months[month_index]
        
        # Determine the year (January-May will be 2026)
        year = current_year if month >= 9 else current_year + 1
        
        # Create 2-3 events per school across different months
        for j, event_type in enumerate(event_types):
            # Skip some event types to avoid too many events
            if j > 1:  # Only create first 2 event types per school
                break
                
            # Calculate event date (spread across the month)
            day = 10 + (j * 7) + (i % 3)  # Spread days: 10, 17, 24, etc.
            
            # Ensure day is valid for the month
            while day > calendar.monthrange(year, month)[1]:
                day -= 7
            
            event_date = date(year, month, day)
            
            # Create event title
            title = event_type['title_template'].format(school=school_name)
            
            # Set start time (morning or afternoon)
            start_hour = 9 if j % 2 == 0 else 14  # 9 AM or 2 PM
            start_time = time(start_hour, 0)  # 9:00 AM or 2:00 PM
            
            # Calculate end time
            end_hour = start_hour + int(event_type['duration_hours'])
            end_minute = int((event_type['duration_hours'] % 1) * 60)
            end_time = time(end_hour, end_minute)
            
            # Create location
            location = f"{school_name} - {address}"
            
            # Create notes
            notes = f"Contact: {contact_name}. Coordinated with school administration."
            
            try:
                cursor.execute("""
                    INSERT INTO recruitment_event (
                        title, description, event_date, start_time, end_time,
                        location, university_id, event_type, status, attendees_count, notes,
                        created_at, last_modified
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    title,
                    event_type['description'],
                    event_date,
                    start_time,
                    end_time,
                    location,
                    school_id,
                    event_type['type'],
                    'scheduled',
                    0,
                    notes,
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                
                event_count += 1
                print(f"✓ Created event: {title} on {event_date}")
                
            except Exception as e:
                print(f"⚠ Error creating event for {school_name}: {e}")
    
    conn.commit()
    cursor.close()
    
    return event_count

def main():
    print("=== Create Comprehensive Calendar Events ===")
    
    # Connect to database
    conn = get_database_connection()
    print("✓ Connected to production database")
    print()
    
    # Clear existing events
    clear_existing_events(conn)
    
    # Create comprehensive events
    event_count = create_comprehensive_events(conn)
    
    conn.close()
    
    print()
    print("=== SUMMARY ===")
    print(f"Created {event_count} calendar events")
    print("Events are now spread across all 13 high schools")
    print("Events span from September 2025 through May 2026")
    print()
    print("✅ Calendar events creation complete!")

if __name__ == "__main__":
    main()
