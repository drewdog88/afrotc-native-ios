#!/usr/bin/env python3
"""
Script to create comprehensive potential recruits from all 13 high schools
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from datetime import datetime
import random

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

def clear_existing_recruits(conn):
    """Clear existing potential recruits"""
    cursor = conn.cursor()
    
    print("Clearing existing potential recruits...")
    
    try:
        cursor.execute("DELETE FROM potential_recruit")
        conn.commit()
        print(f"✓ Cleared {cursor.rowcount} existing recruits")
    except Exception as e:
        print(f"⚠ Error clearing recruits: {e}")
        conn.rollback()
    
    cursor.close()

def create_comprehensive_recruits(conn):
    """Create comprehensive potential recruits from all schools"""
    cursor = conn.cursor()
    
    print("Creating comprehensive potential recruits...")
    
    # Get all schools
    schools = get_school_contacts(conn)
    
    # Sample data for varied recruits
    first_names = [
        "Alex", "Jordan", "Taylor", "Casey", "Morgan", "Riley", "Quinn", "Avery", "Blake", "Cameron",
        "Dakota", "Emerson", "Finley", "Gray", "Harper", "Indigo", "Jamie", "Kendall", "Logan", "Mason",
        "Noah", "Olivia", "Parker", "Quinn", "Rowan", "Sage", "Tyler", "Unity", "Vega", "Winter",
        "Xander", "Yuki", "Zara", "Aiden", "Bella", "Caleb", "Diana", "Ethan", "Faith", "Gabriel",
        "Hannah", "Isaac", "Jade", "Kai", "Luna", "Maya", "Nova", "Owen", "Paisley", "River"
    ]
    
    last_names = [
        "Anderson", "Brown", "Chen", "Davis", "Evans", "Foster", "Garcia", "Harris", "Ivanov", "Johnson",
        "Kim", "Lee", "Martinez", "Nguyen", "O'Connor", "Patel", "Quinn", "Rodriguez", "Smith", "Taylor",
        "Upton", "Valdez", "Wang", "Xu", "Young", "Zhang", "Adams", "Baker", "Clark", "Edwards",
        "Fisher", "Green", "Hall", "Jackson", "King", "Lewis", "Miller", "Nelson", "Parker", "Roberts",
        "Scott", "Thompson", "Walker", "White", "Wilson", "Wood", "Allen", "Carter", "Cooper", "Cox"
    ]
    
    majors = [
        "Aerospace Engineering", "Computer Science", "Mechanical Engineering", "Electrical Engineering",
        "Physics", "Mathematics", "Chemistry", "Biology", "Psychology", "Political Science",
        "International Relations", "Business Administration", "Economics", "History", "English",
        "Environmental Science", "Civil Engineering", "Chemical Engineering", "Biomedical Engineering",
        "Cybersecurity", "Data Science", "Artificial Intelligence", "Robotics", "Aviation Management"
    ]
    
    interests = [
        "Aviation and flight", "Leadership development", "Military history", "Technology and innovation",
        "Public service", "International affairs", "Engineering and design", "Scientific research",
        "Physical fitness", "Team sports", "Debate and public speaking", "Community service",
        "Robotics and automation", "Space exploration", "Cybersecurity", "Environmental protection",
        "Emergency response", "Strategic planning", "Cross-cultural communication", "Problem solving"
    ]
    
    statuses = ["prospective", "interested", "applying", "accepted", "enrolled"]
    
    # Create recruits for each school
    recruit_count = 0
    
    for school_id, school_name, contact_name, address in schools:
        # Create 3-5 recruits per school
        num_recruits = random.randint(3, 5)
        
        for i in range(num_recruits):
            # Generate varied information
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            
            # Create email based on name
            email = f"{first_name.lower()}.{last_name.lower()}@student.{school_name.lower().replace(' ', '').replace('-', '')}.edu"
            
            # Generate phone number
            area_codes = ["206", "425", "360", "503", "971", "541", "360"]
            area_code = random.choice(area_codes)
            phone = f"({area_code}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
            
            # Generate academic information
            gpa = round(random.uniform(2.8, 4.0), 2)
            sat_score = random.randint(1000, 1600) if random.random() > 0.3 else None
            act_score = random.randint(18, 36) if random.random() > 0.3 else None
            
            # Generate graduation year (2025-2027)
            graduation_year = random.randint(2025, 2027)
            
            # Generate major and interests
            major = random.choice(majors)
            num_interests = random.randint(2, 4)
            selected_interests = random.sample(interests, num_interests)
            interests_text = ", ".join(selected_interests)
            
            # Generate status
            status = random.choice(statuses)
            
            # Generate notes
            notes_templates = [
                f"Strong academic performance at {school_name}. Shows leadership potential in school activities.",
                f"Interested in {major}. Has participated in {random.choice(['robotics', 'debate', 'sports', 'community service'])} programs.",
                f"Family has military background. Highly motivated and disciplined student.",
                f"Excellent communication skills. Active in student government and community service.",
                f"Demonstrates strong problem-solving abilities. Interested in technology and innovation.",
                f"Shows natural leadership qualities. Participated in {random.choice(['JROTC', 'scouting', 'team sports', 'academic clubs'])}.",
                f"Strong interest in aviation and aerospace. Has taken relevant coursework.",
                f"Demonstrates commitment to service. Active volunteer in community organizations.",
                f"Excellent academic record with focus on STEM subjects. Shows initiative and drive.",
                f"Interested in international affairs and global perspectives. Strong language skills."
            ]
            notes = random.choice(notes_templates)
            
            # Add some variation based on school location
            if "Seattle" in address:
                notes += " From Seattle area - familiar with local AFROTC opportunities."
            elif "Portland" in address:
                notes += " From Portland area - interested in University of Portland AFROTC program."
            elif "Vancouver" in address:
                notes += " From Vancouver area - considering both Washington and Oregon programs."
            
            try:
                cursor.execute("""
                    INSERT INTO potential_recruit (
                        first_name, last_name, email, phone, major, current_school, school_type,
                        high_school_graduation_year, expected_college_graduation_year, gpa, sat_score,
                        act_score, interests, notes, status, created_at, last_modified
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    first_name,
                    last_name,
                    email,
                    phone,
                    major,
                    school_name,
                    'high_school',
                    graduation_year,
                    graduation_year + 4,  # Expected college graduation
                    gpa,
                    sat_score,
                    act_score,
                    interests_text,
                    notes,
                    status,
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                
                recruit_count += 1
                print(f"✓ Created recruit: {first_name} {last_name} from {school_name}")
                
            except Exception as e:
                print(f"⚠ Error creating recruit for {school_name}: {e}")
    
    conn.commit()
    cursor.close()
    
    return recruit_count

def main():
    print("=== Create Comprehensive Potential Recruits ===")
    
    # Connect to database
    conn = get_database_connection()
    print("✓ Connected to production database")
    print()
    
    # Clear existing recruits
    clear_existing_recruits(conn)
    
    # Create comprehensive recruits
    recruit_count = create_comprehensive_recruits(conn)
    
    conn.close()
    
    print()
    print("=== SUMMARY ===")
    print(f"Created {recruit_count} potential recruits")
    print("Recruits are now spread across all 13 high schools")
    print("Each recruit has varied academic and personal information")
    print()
    print("✅ Potential recruits creation complete!")

if __name__ == "__main__":
    main()
