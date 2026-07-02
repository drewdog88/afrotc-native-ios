import os
import unittest
from datetime import datetime, date
from app_local import app, db, User, PotentialRecruit, Cadet, UniversityContact, RecruitmentEvent, ExternalLink, RecruitmentDocument, ActivityLog, PasswordHistory
from werkzeug.security import generate_password_hash
from sqlalchemy import text

class TestDatabaseOperations(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        with app.app_context():
            # Clean database
            db.session.execute(text('DROP SCHEMA public CASCADE'))
            db.session.execute(text('CREATE SCHEMA public'))
            db.session.commit()
            
            # Create all tables
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.session.execute(text('DROP SCHEMA public CASCADE'))
            db.session.execute(text('CREATE SCHEMA public'))
            db.session.commit()

    def test_user_crud_operations(self):
        """Test User model CRUD operations"""
        with app.app_context():
            # CREATE
            user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('TestPass123!'),
                first_name='Test',
                last_name='User',
                phone='555-1234',
                role='recruiter',
                secret_question='What is your favorite color?',
                secret_answer_hash=generate_password_hash('blue')
            )
            db.session.add(user)
            db.session.commit()
            
            # READ
            retrieved_user = User.query.filter_by(username='testuser').first()
            self.assertIsNotNone(retrieved_user)
            self.assertEqual(retrieved_user.email, 'test@example.com')
            self.assertEqual(retrieved_user.first_name, 'Test')
            self.assertEqual(retrieved_user.role, 'recruiter')
            
            # UPDATE
            retrieved_user.phone = '555-5678'
            retrieved_user.role = 'admin'
            db.session.commit()
            
            updated_user = User.query.get(retrieved_user.id)
            self.assertEqual(updated_user.phone, '555-5678')
            self.assertEqual(updated_user.role, 'admin')
            
            # DELETE
            user_id = updated_user.id
            db.session.delete(updated_user)
            db.session.commit()
            
            deleted_user = User.query.get(user_id)
            self.assertIsNone(deleted_user)

    def test_potential_recruit_crud_operations(self):
        """Test PotentialRecruit model CRUD operations"""
        with app.app_context():
            # CREATE
            recruit = PotentialRecruit(
                first_name='John',
                last_name='Doe',
                email='john.doe@example.com',
                phone='555-1111',
                current_school='Test High School',
                school_type='high_school',
                high_school_graduation_year=2024,
                gpa=3.5,
                major='Engineering',
                interests='Aviation, Leadership',
                status='contacted'
            )
            db.session.add(recruit)
            db.session.commit()
            
            # READ
            retrieved_recruit = PotentialRecruit.query.filter_by(email='john.doe@example.com').first()
            self.assertIsNotNone(retrieved_recruit)
            self.assertEqual(retrieved_recruit.first_name, 'John')
            self.assertEqual(retrieved_recruit.current_school, 'Test High School')
            self.assertEqual(retrieved_recruit.gpa, 3.5)
            
            # UPDATE
            retrieved_recruit.status = 'enrolled'
            retrieved_recruit.gpa = 3.7
            db.session.commit()
            
            updated_recruit = PotentialRecruit.query.get(retrieved_recruit.id)
            self.assertEqual(updated_recruit.status, 'enrolled')
            self.assertEqual(updated_recruit.gpa, 3.7)
            
            # DELETE
            recruit_id = updated_recruit.id
            db.session.delete(updated_recruit)
            db.session.commit()
            
            deleted_recruit = PotentialRecruit.query.get(recruit_id)
            self.assertIsNone(deleted_recruit)

    def test_cadet_crud_operations(self):
        """Test Cadet model CRUD operations"""
        with app.app_context():
            # CREATE
            cadet = Cadet(
                first_name='Jane',
                last_name='Smith',
                email='jane.smith@example.com',
                phone='555-2222',
                major='Computer Science',
                graduation_year=2025,
                cadet_rank='C/Capt',
                hometown='Portland, OR',
                officer_interest='Pilot',
                status='active',
                gpa=3.8
            )
            db.session.add(cadet)
            db.session.commit()
            
            # READ
            retrieved_cadet = Cadet.query.filter_by(email='jane.smith@example.com').first()
            self.assertIsNotNone(retrieved_cadet)
            self.assertEqual(retrieved_cadet.first_name, 'Jane')
            self.assertEqual(retrieved_cadet.major, 'Computer Science')
            self.assertEqual(retrieved_cadet.cadet_rank, 'C/Capt')
            
            # UPDATE
            retrieved_cadet.cadet_rank = 'C/Maj'
            retrieved_cadet.gpa = 3.9
            db.session.commit()
            
            updated_cadet = Cadet.query.get(retrieved_cadet.id)
            self.assertEqual(updated_cadet.cadet_rank, 'C/Maj')
            self.assertEqual(updated_cadet.gpa, 3.9)
            
            # DELETE
            cadet_id = updated_cadet.id
            db.session.delete(updated_cadet)
            db.session.commit()
            
            deleted_cadet = Cadet.query.get(cadet_id)
            self.assertIsNone(deleted_cadet)

    def test_university_contact_crud_operations(self):
        """Test UniversityContact model CRUD operations"""
        with app.app_context():
            # CREATE
            contact = UniversityContact(
                contact_name='Dr. Johnson',
                contact_title='Professor',
                university_name='University of Portland',
                email='dr.johnson@up.edu',
                phone='503-555-3333'
            )
            db.session.add(contact)
            db.session.commit()
            
            # READ
            retrieved_contact = UniversityContact.query.filter_by(email='dr.johnson@up.edu').first()
            self.assertIsNotNone(retrieved_contact)
            self.assertEqual(retrieved_contact.contact_name, 'Dr. Johnson')
            self.assertEqual(retrieved_contact.university_name, 'University of Portland')
            
            # UPDATE
            retrieved_contact.contact_title = 'Department Chair'
            retrieved_contact.phone = '503-555-4444'
            db.session.commit()
            
            updated_contact = UniversityContact.query.get(retrieved_contact.id)
            self.assertEqual(updated_contact.contact_title, 'Department Chair')
            self.assertEqual(updated_contact.phone, '503-555-4444')
            
            # DELETE
            contact_id = updated_contact.id
            db.session.delete(updated_contact)
            db.session.commit()
            
            deleted_contact = UniversityContact.query.get(contact_id)
            self.assertIsNone(deleted_contact)

    def test_recruitment_event_crud_operations(self):
        """Test RecruitmentEvent model CRUD operations"""
        with app.app_context():
            # CREATE
            event = RecruitmentEvent(
                title='Career Fair',
                event_date=date(2024, 3, 15),
                location='Student Union',
                description='Annual career fair for students',
                event_type='career_fair',
                attendees_count=100
            )
            db.session.add(event)
            db.session.commit()
            
            # READ
            retrieved_event = RecruitmentEvent.query.filter_by(title='Career Fair').first()
            self.assertIsNotNone(retrieved_event)
            self.assertEqual(retrieved_event.location, 'Student Union')
            self.assertEqual(retrieved_event.attendees_count, 100)
            
            # UPDATE
            retrieved_event.attendees_count = 150
            retrieved_event.location = 'Main Auditorium'
            db.session.commit()
            
            updated_event = RecruitmentEvent.query.get(retrieved_event.id)
            self.assertEqual(updated_event.attendees_count, 150)
            self.assertEqual(updated_event.location, 'Main Auditorium')
            
            # DELETE
            event_id = updated_event.id
            db.session.delete(updated_event)
            db.session.commit()
            
            deleted_event = RecruitmentEvent.query.get(event_id)
            self.assertIsNone(deleted_event)

    def test_external_link_crud_operations(self):
        """Test ExternalLink model CRUD operations"""
        with app.app_context():
            # CREATE
            link = ExternalLink(
                title='Air Force Website',
                url='https://www.airforce.com',
                description='Official Air Force website',
                category='official'
            )
            db.session.add(link)
            db.session.commit()
            
            # READ
            retrieved_link = ExternalLink.query.filter_by(title='Air Force Website').first()
            self.assertIsNotNone(retrieved_link)
            self.assertEqual(retrieved_link.url, 'https://www.airforce.com')
            self.assertEqual(retrieved_link.category, 'official')
            
            # UPDATE
            retrieved_link.url = 'https://www.af.mil'
            retrieved_link.description = 'Updated official Air Force website'
            db.session.commit()
            
            updated_link = ExternalLink.query.get(retrieved_link.id)
            self.assertEqual(updated_link.url, 'https://www.af.mil')
            self.assertEqual(updated_link.description, 'Updated official Air Force website')
            
            # DELETE
            link_id = updated_link.id
            db.session.delete(updated_link)
            db.session.commit()
            
            deleted_link = ExternalLink.query.get(link_id)
            self.assertIsNone(deleted_link)

    def test_recruitment_document_crud_operations(self):
        """Test RecruitmentDocument model CRUD operations"""
        with app.app_context():
            # CREATE
            document = RecruitmentDocument(
                title='Recruitment Brochure',
                filename='brochure.pdf',
                original_filename='brochure.pdf',
                category='brochure',
                description='Main recruitment brochure for 2024'
            )
            db.session.add(document)
            db.session.commit()
            
            # READ
            retrieved_doc = RecruitmentDocument.query.filter_by(title='Recruitment Brochure').first()
            self.assertIsNotNone(retrieved_doc)
            self.assertEqual(retrieved_doc.filename, 'brochure.pdf')
            self.assertEqual(retrieved_doc.category, 'brochure')
            
            # UPDATE
            retrieved_doc.filename = 'updated_brochure.pdf'
            retrieved_doc.description = 'Updated recruitment brochure for 2024'
            db.session.commit()
            
            updated_doc = RecruitmentDocument.query.get(retrieved_doc.id)
            self.assertEqual(updated_doc.filename, 'updated_brochure.pdf')
            self.assertEqual(updated_doc.description, 'Updated recruitment brochure for 2024')
            
            # DELETE
            doc_id = updated_doc.id
            db.session.delete(updated_doc)
            db.session.commit()
            
            deleted_doc = RecruitmentDocument.query.get(doc_id)
            self.assertIsNone(deleted_doc)

    def test_activity_log_crud_operations(self):
        """Test ActivityLog model CRUD operations"""
        with app.app_context():
            # First create a user for the activity log
            user = User(
                username='loguser',
                email='log@example.com',
                password_hash=generate_password_hash('TestPass123!'),
                first_name='Log',
                last_name='User',
                role='admin',
                secret_question='Test question?',
                secret_answer_hash=generate_password_hash('answer')
            )
            db.session.add(user)
            db.session.commit()
            
            # CREATE
            activity = ActivityLog(
                user_id=user.id,
                username=user.username,
                action='LOGIN',
                details='User logged in successfully'
            )
            db.session.add(activity)
            db.session.commit()
            
            # READ
            retrieved_activity = ActivityLog.query.filter_by(action='LOGIN').first()
            self.assertIsNotNone(retrieved_activity)
            self.assertEqual(retrieved_activity.user_id, user.id)
            self.assertEqual(retrieved_activity.details, 'User logged in successfully')
            
            # UPDATE (ActivityLog typically doesn't get updated, but testing the capability)
            retrieved_activity.details = 'User logged in successfully - updated'
            db.session.commit()
            
            updated_activity = ActivityLog.query.get(retrieved_activity.id)
            self.assertEqual(updated_activity.details, 'User logged in successfully - updated')
            
            # DELETE
            activity_id = updated_activity.id
            db.session.delete(updated_activity)
            db.session.commit()
            
            deleted_activity = ActivityLog.query.get(activity_id)
            self.assertIsNone(deleted_activity)

    def test_password_history_crud_operations(self):
        """Test PasswordHistory model CRUD operations"""
        with app.app_context():
            # First create a user for the password history
            user = User(
                username='passuser',
                email='pass@example.com',
                password_hash=generate_password_hash('TestPass123!'),
                first_name='Pass',
                last_name='User',
                role='admin',
                secret_question='Test question?',
                secret_answer_hash=generate_password_hash('answer')
            )
            db.session.add(user)
            db.session.commit()
            
            # CREATE
            password_history = PasswordHistory(
                user_id=user.id,
                password_hash=generate_password_hash('OldPass123!')
            )
            db.session.add(password_history)
            db.session.commit()
            
            # READ
            retrieved_history = PasswordHistory.query.filter_by(user_id=user.id).first()
            self.assertIsNotNone(retrieved_history)
            self.assertEqual(retrieved_history.user_id, user.id)
            
            # UPDATE (PasswordHistory typically doesn't get updated, but testing the capability)
            old_hash = retrieved_history.password_hash
            retrieved_history.password_hash = generate_password_hash('NewerOldPass123!')
            db.session.commit()
            
            updated_history = PasswordHistory.query.get(retrieved_history.id)
            self.assertNotEqual(updated_history.password_hash, old_hash)
            
            # DELETE
            history_id = updated_history.id
            db.session.delete(updated_history)
            db.session.commit()
            
            deleted_history = PasswordHistory.query.get(history_id)
            self.assertIsNone(deleted_history)

    def test_database_relationships(self):
        """Test database relationships between models"""
        with app.app_context():
            # Create a user
            user = User(
                username='reluser',
                email='rel@example.com',
                password_hash=generate_password_hash('TestPass123!'),
                first_name='Rel',
                last_name='User',
                role='admin',
                secret_question='Test question?',
                secret_answer_hash=generate_password_hash('answer')
            )
            db.session.add(user)
            db.session.commit()
            
            # Create activity log for this user
            activity = ActivityLog(
                user_id=user.id,
                username=user.username,
                action='TEST',
                details='Testing relationship'
            )
            db.session.add(activity)
            
            # Create password history for this user
            password_history = PasswordHistory(
                user_id=user.id,
                password_hash=generate_password_hash('OldPass123!')
            )
            db.session.add(password_history)
            db.session.commit()
            
            # Test relationships
            retrieved_user = User.query.get(user.id)
            
            # Check if we can access related activity logs
            user_activities = ActivityLog.query.filter_by(user_id=user.id).all()
            self.assertEqual(len(user_activities), 1)
            self.assertEqual(user_activities[0].action, 'TEST')
            
            # Check if we can access related password history
            user_password_history = PasswordHistory.query.filter_by(user_id=user.id).all()
            self.assertEqual(len(user_password_history), 1)

if __name__ == '__main__':
    unittest.main()
