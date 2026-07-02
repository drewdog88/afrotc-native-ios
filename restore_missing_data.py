#!/usr/bin/env python3
"""
Script to restore missing recruitment materials, external links, and calendar events
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from datetime import datetime, date, time

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

def restore_recruitment_events(conn):
    """Restore recruitment events data"""
    cursor = conn.cursor()
    
    print("Restoring recruitment events...")
    
    # Sample recruitment events
    events = [
        {
            'title': 'AFROTC Information Session',
            'description': 'General information session about AFROTC opportunities and requirements',
            'event_date': date(2025, 9, 15),
            'start_time': time(14, 0),
            'end_time': time(15, 30),
            'location': 'University of Portland - Buckley Center 163',
            'event_type': 'information_session',
            'status': 'scheduled',
            'attendees_count': 0,
            'notes': 'Open to all interested students'
        },
        {
            'title': 'High School Visit - Jesuit High School',
            'description': 'Recruitment visit to Jesuit High School to present AFROTC opportunities',
            'event_date': date(2025, 9, 20),
            'start_time': time(10, 0),
            'end_time': time(11, 30),
            'location': 'Jesuit High School - Portland',
            'event_type': 'high_school_visit',
            'status': 'scheduled',
            'attendees_count': 0,
            'notes': 'Coordinated with school counselor'
        },
        {
            'title': 'College Fair - Portland State University',
            'description': 'Represent AFROTC at PSU college fair',
            'event_date': date(2025, 10, 5),
            'start_time': time(9, 0),
            'end_time': time(16, 0),
            'location': 'Portland State University - Smith Memorial Student Union',
            'event_type': 'college_fair',
            'status': 'scheduled',
            'attendees_count': 0,
            'notes': 'Bring recruitment materials and display'
        },
        {
            'title': 'Leadership Lab',
            'description': 'Hands-on leadership training for current cadets',
            'event_date': date(2025, 9, 25),
            'start_time': time(13, 0),
            'end_time': time(17, 0),
            'location': 'University of Portland - Campus',
            'event_type': 'training',
            'status': 'scheduled',
            'attendees_count': 0,
            'notes': 'Required for all cadets'
        }
    ]
    
    for event in events:
        try:
            cursor.execute("""
                INSERT INTO recruitment_event (
                    title, description, event_date, start_time, end_time,
                    location, event_type, status, attendees_count, notes,
                    created_at, last_modified
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                event['title'],
                event['description'],
                event['event_date'],
                event['start_time'],
                event['end_time'],
                event['location'],
                event['event_type'],
                event['status'],
                event['attendees_count'],
                event['notes'],
                datetime.utcnow(),
                datetime.utcnow()
            ))
            print(f"✓ Restored event: {event['title']}")
        except Exception as e:
            print(f"⚠ Error restoring event {event['title']}: {e}")
    
    conn.commit()
    cursor.close()

def restore_external_links(conn):
    """Restore external links data"""
    cursor = conn.cursor()
    
    print("Restoring external links...")
    
    # Sample external links
    links = [
        {
            'title': 'AFROTC Official Website',
            'url': 'https://www.afrotc.com/',
            'description': 'Official Air Force ROTC website with general information',
            'category': 'official',
            'is_active': True,
            'sort_order': 1
        },
        {
            'title': 'University of Portland AFROTC',
            'url': 'https://www.up.edu/afrotc/',
            'description': 'Detachment 695 official page at University of Portland',
            'category': 'official',
            'is_active': True,
            'sort_order': 2
        },
        {
            'title': 'Air Force Careers',
            'url': 'https://www.airforce.com/careers',
            'description': 'Explore Air Force career opportunities and requirements',
            'category': 'resources',
            'is_active': True,
            'sort_order': 3
        },
        {
            'title': 'AFROTC Scholarship Information',
            'url': 'https://www.afrotc.com/scholarships',
            'description': 'Information about AFROTC scholarships and financial aid',
            'category': 'resources',
            'is_active': True,
            'sort_order': 4
        },
        {
            'title': 'Physical Fitness Standards',
            'url': 'https://www.afrotc.com/fitness',
            'description': 'Physical fitness requirements and standards for AFROTC',
            'category': 'resources',
            'is_active': True,
            'sort_order': 5
        }
    ]
    
    for link in links:
        try:
            cursor.execute("""
                INSERT INTO external_link (
                    title, url, description, category, is_active, sort_order,
                    created_at, last_modified
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                link['title'],
                link['url'],
                link['description'],
                link['category'],
                link['is_active'],
                link['sort_order'],
                datetime.utcnow(),
                datetime.utcnow()
            ))
            print(f"✓ Restored link: {link['title']}")
        except Exception as e:
            print(f"⚠ Error restoring link {link['title']}: {e}")
    
    conn.commit()
    cursor.close()

def restore_recruitment_documents(conn):
    """Restore recruitment documents data"""
    cursor = conn.cursor()
    
    print("Restoring recruitment documents...")
    
    # Sample recruitment documents (these would be uploaded to Vercel Blob)
    documents = [
        {
            'title': 'AFROTC Information Brochure',
            'description': 'General information about AFROTC program and benefits',
            'filename': 'afrotc_info_brochure.pdf',
            'original_filename': 'AFROTC_Information_Brochure.pdf',
            'file_size': 2048576,  # 2MB
            'file_type': 'pdf',
            'category': 'brochures',
            'is_active': True,
            'sort_order': 1
        },
        {
            'title': 'Scholarship Application Guide',
            'description': 'Step-by-step guide for applying to AFROTC scholarships',
            'filename': 'scholarship_guide.pdf',
            'original_filename': 'AFROTC_Scholarship_Guide.pdf',
            'file_size': 1536000,  # 1.5MB
            'file_type': 'pdf',
            'category': 'guides',
            'is_active': True,
            'sort_order': 2
        },
        {
            'title': 'Physical Fitness Standards',
            'description': 'Detailed physical fitness requirements and testing procedures',
            'filename': 'fitness_standards.pdf',
            'original_filename': 'Physical_Fitness_Standards.pdf',
            'file_size': 1024000,  # 1MB
            'file_type': 'pdf',
            'category': 'guides',
            'is_active': True,
            'sort_order': 3
        },
        {
            'title': 'Leadership Development Program',
            'description': 'Overview of leadership training and development opportunities',
            'filename': 'leadership_program.pptx',
            'original_filename': 'Leadership_Development_Program.pptx',
            'file_size': 5120000,  # 5MB
            'file_type': 'pptx',
            'category': 'presentations',
            'is_active': True,
            'sort_order': 4
        }
    ]
    
    for doc in documents:
        try:
            cursor.execute("""
                INSERT INTO recruitment_document (
                    title, description, filename, original_filename, file_size,
                    file_type, category, is_active, sort_order,
                    created_at, last_modified
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                doc['title'],
                doc['description'],
                doc['filename'],
                doc['original_filename'],
                doc['file_size'],
                doc['file_type'],
                doc['category'],
                doc['is_active'],
                doc['sort_order'],
                datetime.utcnow(),
                datetime.utcnow()
            ))
            print(f"✓ Restored document: {doc['title']}")
        except Exception as e:
            print(f"⚠ Error restoring document {doc['title']}: {e}")
    
    conn.commit()
    cursor.close()

def restore_university_contacts(conn):
    """Restore university contacts data"""
    cursor = conn.cursor()
    
    print("Restoring university contacts...")
    
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

def check_existing_data(conn):
    """Check what data already exists"""
    cursor = conn.cursor()
    
    print("Checking existing data...")
    
    # Check recruitment events
    cursor.execute("SELECT COUNT(*) FROM recruitment_event")
    event_count = cursor.fetchone()[0]
    print(f"✓ Found {event_count} existing recruitment events")
    
    # Check external links
    cursor.execute("SELECT COUNT(*) FROM external_link")
    link_count = cursor.fetchone()[0]
    print(f"✓ Found {link_count} existing external links")
    
    # Check recruitment documents
    cursor.execute("SELECT COUNT(*) FROM recruitment_document")
    doc_count = cursor.fetchone()[0]
    print(f"✓ Found {doc_count} existing recruitment documents")
    
    # Check university contacts
    cursor.execute("SELECT COUNT(*) FROM university_contact")
    contact_count = cursor.fetchone()[0]
    print(f"✓ Found {contact_count} existing university contacts")
    
    cursor.close()
    
    return event_count, link_count, doc_count, contact_count

def main():
    print("=== Restore Missing Data ===")
    
    # Connect to database
    conn = get_database_connection()
    print("✓ Connected to production database")
    
    # Check existing data
    event_count, link_count, doc_count, contact_count = check_existing_data(conn)
    
    # Only restore if data is missing
    if event_count == 0:
        restore_recruitment_events(conn)
    else:
        print("⚠ Recruitment events already exist, skipping...")
    
    if link_count == 0:
        restore_external_links(conn)
    else:
        print("⚠ External links already exist, skipping...")
    
    if doc_count == 0:
        restore_recruitment_documents(conn)
    else:
        print("⚠ Recruitment documents already exist, skipping...")
    
    if contact_count == 0:
        restore_university_contacts(conn)
    else:
        print("⚠ University contacts already exist, skipping...")
    
    conn.close()
    print("\n=== Data restore complete ===")
    print("Materials, links, calendar events, and outreach contacts should now be available!")

if __name__ == "__main__":
    main()
