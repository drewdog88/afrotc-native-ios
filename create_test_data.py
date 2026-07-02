import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from app_local import app, db, User, PotentialRecruit, Cadet, UniversityContact, RecruitmentEvent, RecruitmentDocument, ExternalLink, ActivityLog

# Load environment variables
load_dotenv('env.local')

def create_test_data():
    """Create test data for local development"""
    with app.app_context():
        print("Creating test data...")
        
        # Create test users
        users = [
            {
                'username': 'admin',  # Keep existing admin
                'email': 'admin@afrotc695.com',
                'password': 'admin123',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'admin',
                'secret_question': 'What is your favorite color?',
                'secret_answer': 'blue'
            },
            {
                'username': 'recruiter1',
                'email': 'recruiter1@afrotc695.com',
                'password': 'Password123!',
                'first_name': 'John',
                'last_name': 'Smith',
                'role': 'recruiter',
                'secret_question': 'What is your favorite food?',
                'secret_answer': 'pizza'
            }
        ]
        
        for user_data in users:
            if not User.query.filter_by(username=user_data['username']).first():
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=generate_password_hash(user_data['password']),
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    role=user_data['role'],
                    secret_question=user_data['secret_question'],
                    secret_answer_hash=generate_password_hash(user_data['secret_answer'])
                )
                db.session.add(user)
                print(f"Created user: {user.username}")
        
        # Create test potential recruits
        recruits = [
            {
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'email': 'sarah.j@example.com',
                'phone': '555-0101',
                'major': 'Computer Science',
                'current_school': 'Tech High School',
                'school_type': 'high_school',
                'high_school_graduation_year': 2024,
                'expected_college_graduation_year': 2028,
                'gpa': 3.8,
                'sat_score': 1450,
                'act_score': 32,
                'interests': 'Cybersecurity, Programming',
                'notes': 'Strong academic performance',
                'status': 'prospective'
            },
            {
                'first_name': 'Michael',
                'last_name': 'Chen',
                'email': 'mchen@example.com',
                'phone': '555-0102',
                'major': 'Aerospace Engineering',
                'current_school': 'State University',
                'school_type': 'college',
                'high_school_graduation_year': 2023,
                'expected_college_graduation_year': 2027,
                'gpa': 3.6,
                'interests': 'Aircraft Design, Space Systems',
                'notes': 'Transfer student with strong interest in Air Force',
                'status': 'interested'
            }
        ]
        
        for recruit_data in recruits:
            recruit = PotentialRecruit(**recruit_data)
            db.session.add(recruit)
            print(f"Created recruit: {recruit.first_name} {recruit.last_name}")
        
        # Create test cadets
        cadets = [
            {
                'first_name': 'James',
                'last_name': 'Wilson',
                'email': 'jwilson@afrotc.edu',
                'phone': '555-0201',
                'major': 'Mechanical Engineering',
                'graduation_year': 2025,
                'cadet_rank': 'Cadet Captain',
                'hometown': 'Chicago, IL',
                'officer_interest': 'Pilot',
                'status': 'active',
                'gpa': 3.7
            },
            {
                'first_name': 'Emily',
                'last_name': 'Martinez',
                'email': 'emartinez@afrotc.edu',
                'phone': '555-0202',
                'major': 'International Relations',
                'graduation_year': 2024,
                'cadet_rank': 'Cadet Major',
                'hometown': 'Miami, FL',
                'officer_interest': 'Intelligence Officer',
                'status': 'active',
                'gpa': 3.9
            }
        ]
        
        for cadet_data in cadets:
            cadet = Cadet(**cadet_data)
            db.session.add(cadet)
            print(f"Created cadet: {cadet.first_name} {cadet.last_name}")
        
        # Create test university contacts
        contacts = [
            {
                'university_name': 'State University',
                'contact_name': 'Dr. Robert Brown',
                'contact_title': 'Dean of Engineering',
                'email': 'rbrown@stateuniv.edu',
                'phone': '555-0301',
                'address': '123 University Ave, College Town, ST 12345',
                'notes': 'Strong engineering program partnership'
            },
            {
                'university_name': 'Tech Institute',
                'contact_name': 'Prof. Lisa Wong',
                'contact_title': 'Department Chair - Computer Science',
                'email': 'lwong@techinst.edu',
                'phone': '555-0302',
                'address': '456 Tech Blvd, Innovation City, ST 67890',
                'notes': 'Interested in cybersecurity collaboration'
            }
        ]
        
        for contact_data in contacts:
            contact = UniversityContact(**contact_data)
            db.session.add(contact)
            print(f"Created contact: {contact.contact_name}")
        
        # Create test events
        events = [
            {
                'title': 'Spring Recruitment Fair',
                'description': 'Annual spring recruitment event at State University',
                'event_date': datetime.now().date() + timedelta(days=30),
                'start_time': datetime.strptime('10:00', '%H:%M').time(),
                'end_time': datetime.strptime('15:00', '%H:%M').time(),
                'location': 'State University Student Center',
                'event_type': 'recruitment_fair',
                'status': 'scheduled'
            },
            {
                'title': 'Tech Institute Info Session',
                'description': 'Information session for Computer Science students',
                'event_date': datetime.now().date() + timedelta(days=45),
                'start_time': datetime.strptime('14:00', '%H:%M').time(),
                'end_time': datetime.strptime('16:00', '%H:%M').time(),
                'location': 'Tech Institute Room 101',
                'event_type': 'info_session',
                'status': 'scheduled'
            }
        ]
        
        for event_data in events:
            event = RecruitmentEvent(**event_data)
            db.session.add(event)
            print(f"Created event: {event.title}")
        
        # Create test external links
        links = [
            {
                'title': 'Air Force ROTC Homepage',
                'url': 'https://www.afrotc.com',
                'description': 'Official Air Force ROTC website',
                'category': 'official'
            },
            {
                'title': 'AFROTC Scholarship Information',
                'url': 'https://www.afrotc.com/scholarships',
                'description': 'Information about AFROTC scholarship opportunities',
                'category': 'resources'
            }
        ]
        
        for link_data in links:
            link = ExternalLink(**link_data)
            db.session.add(link)
            print(f"Created link: {link.title}")
        
        # Commit all changes
        try:
            db.session.commit()
            print("All test data created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating test data: {e}")
            raise

if __name__ == '__main__':
    create_test_data()

