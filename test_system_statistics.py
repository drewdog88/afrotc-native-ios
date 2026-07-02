#!/usr/bin/env python3
"""
Unit tests for System Statistics functionality
Tests all helper functions and the main system statistics route
"""

import unittest
import sys
import os
from datetime import datetime, timedelta, date
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.app import app, db, get_database_size, get_record_counts, get_system_performance, get_user_activity_stats, get_recruitment_stats
from api.app import User, PotentialRecruit, Cadet, UniversityContact, RecruitmentEvent, ExternalLink, RecruitmentDocument, ActivityLog, PasswordHistory

class TestSystemStatistics(unittest.TestCase):
    """Test cases for system statistics functionality"""
    
    def setUp(self):
        """Set up test environment"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
            
            # Create test data
            self.create_test_data()
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def create_test_data(self):
        """Create test data for statistics"""
        # Create test users
        user1 = User(
            username='testuser1',
            email='test1@example.com',
            password_hash='hash1',
            first_name='Test',
            last_name='User1',
            secret_question='What is your favorite color?',
            secret_answer_hash='hash1',
            role='admin'
        )
        user2 = User(
            username='testuser2',
            email='test2@example.com',
            password_hash='hash2',
            first_name='Test',
            last_name='User2',
            secret_question='What is your favorite color?',
            secret_answer_hash='hash2',
            role='recruiter'
        )
        db.session.add_all([user1, user2])
        db.session.commit()
        
        # Create test recruits
        recruit1 = PotentialRecruit(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            current_school='Test High School',
            school_type='high_school',
            status='prospective'
        )
        recruit2 = PotentialRecruit(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            current_school='Test College',
            school_type='college',
            status='enrolled'
        )
        db.session.add_all([recruit1, recruit2])
        db.session.commit()
        
        # Create test cadets
        cadet1 = Cadet(
            first_name='Bob',
            last_name='Johnson',
            email='bob@example.com',
            major='Computer Science',
            graduation_year=2025,
            cadet_rank='C/2d Lt',
            status='active'
        )
        cadet2 = Cadet(
            first_name='Alice',
            last_name='Brown',
            email='alice@example.com',
            major='Engineering',
            graduation_year=2024,
            cadet_rank='C/Capt',
            status='graduated'
        )
        db.session.add_all([cadet1, cadet2])
        db.session.commit()
        
        # Create test activity logs
        log1 = ActivityLog(
            user_id=user1.id,
            username=user1.username,
            action='LOGIN',
            table_name='user',
            record_id=user1.id,
            record_description='User login',
            created_at=datetime.utcnow() - timedelta(days=1)
        )
        log2 = ActivityLog(
            user_id=user2.id,
            username=user2.username,
            action='CREATE',
            table_name='potential_recruit',
            record_id=recruit1.id,
            record_description='Created recruit',
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
        db.session.add_all([log1, log2])
        db.session.commit()
    
    def test_get_database_size(self):
        """Test database size calculation"""
        with app.app_context():
            result = get_database_size()
            
            # Should return a dictionary with expected keys
            self.assertIsInstance(result, dict)
            self.assertIn('database', result)
            self.assertIn('total_size_mb', result)
            self.assertIn('data_size_mb', result)
            self.assertIn('index_size_mb', result)
            self.assertIn('table_count', result)
            
            # Values should be numeric
            self.assertIsInstance(result['total_size_mb'], (int, float))
            self.assertIsInstance(result['data_size_mb'], (int, float))
            self.assertIsInstance(result['index_size_mb'], (int, float))
            self.assertIsInstance(result['table_count'], int)
            
            # Should be non-negative
            self.assertGreaterEqual(result['total_size_mb'], 0)
            self.assertGreaterEqual(result['data_size_mb'], 0)
            self.assertGreaterEqual(result['index_size_mb'], 0)
            self.assertGreaterEqual(result['table_count'], 0)
    
    def test_get_record_counts(self):
        """Test record counting functionality"""
        with app.app_context():
            result = get_record_counts()
            
            # Should return a dictionary
            self.assertIsInstance(result, dict)
            
            # Should have counts for all expected tables
            expected_tables = ['user', 'potential_recruit', 'cadet', 'university_contact', 
                             'recruitment_event', 'external_link', 'recruitment_document', 
                             'activity_log', 'password_history']
            
            for table in expected_tables:
                self.assertIn(table, result)
                self.assertIsInstance(result[table], int)
                self.assertGreaterEqual(result[table], 0)
            
            # Should have correct counts for our test data
            self.assertEqual(result['user'], 2)  # 2 test users
            self.assertEqual(result['potential_recruit'], 2)  # 2 test recruits
            self.assertEqual(result['cadet'], 2)  # 2 test cadets
            self.assertEqual(result['activity_log'], 2)  # 2 test logs
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_system_performance(self, mock_disk, mock_memory, mock_cpu):
        """Test system performance metrics"""
        # Mock psutil responses
        mock_cpu.return_value = 25.5
        mock_memory.return_value = MagicMock(
            percent=60.0,
            used=1024 * 1024 * 1024,  # 1GB
            total=2048 * 1024 * 1024   # 2GB
        )
        mock_disk.return_value = MagicMock(
            percent=45.0,
            used=50 * 1024 * 1024 * 1024,  # 50GB
            total=100 * 1024 * 1024 * 1024  # 100GB
        )
        
        with app.app_context():
            result = get_system_performance()
            
            # Should return a dictionary with expected keys
            self.assertIsInstance(result, dict)
            expected_keys = ['cpu_percent', 'memory_percent', 'memory_used_mb', 
                           'memory_total_mb', 'disk_percent', 'disk_used_mb', 'disk_total_mb']
            
            for key in expected_keys:
                self.assertIn(key, result)
                self.assertIsInstance(result[key], (int, float))
                self.assertGreaterEqual(result[key], 0)
            
            # Should have correct values from mocked psutil
            self.assertEqual(result['cpu_percent'], 25.5)
            self.assertEqual(result['memory_percent'], 60.0)
            self.assertEqual(result['memory_used_mb'], 1024.0)
            self.assertEqual(result['memory_total_mb'], 2048.0)
            self.assertEqual(result['disk_percent'], 45.0)
            self.assertEqual(result['disk_used_mb'], 51200.0)
            self.assertEqual(result['disk_total_mb'], 102400.0)
    
    def test_get_user_activity_stats(self):
        """Test user activity statistics"""
        with app.app_context():
            result = get_user_activity_stats()
            
            # Should return a dictionary with expected keys
            self.assertIsInstance(result, dict)
            expected_keys = ['recent_logins', 'active_users', 'total_users', 
                           'recent_activity', 'most_active_users']
            
            for key in expected_keys:
                self.assertIn(key, result)
            
            # Should have correct counts
            self.assertEqual(result['total_users'], 2)  # 2 test users
            self.assertGreaterEqual(result['recent_logins'], 1)  # At least 1 login in last 30 days
            self.assertGreaterEqual(result['recent_activity'], 1)  # At least 1 activity in last 24 hours
            
            # Most active users should be a list
            self.assertIsInstance(result['most_active_users'], list)
    
    def test_get_recruitment_stats(self):
        """Test recruitment statistics"""
        with app.app_context():
            result = get_recruitment_stats()
            
            # Should return a dictionary with expected keys
            self.assertIsInstance(result, dict)
            expected_keys = ['recruit_status_counts', 'cadet_status_counts', 
                           'recent_recruits', 'recent_cadets', 'upcoming_events']
            
            for key in expected_keys:
                self.assertIn(key, result)
            
            # Should have correct counts
            self.assertEqual(result['recent_recruits'], 2)  # 2 recruits created recently
            self.assertEqual(result['recent_cadets'], 2)  # 2 cadets created recently
            
            # Status counts should be lists
            self.assertIsInstance(result['recruit_status_counts'], list)
            self.assertIsInstance(result['cadet_status_counts'], list)
            
            # Should have status counts for our test data
            recruit_statuses = [s['status'] for s in result['recruit_status_counts']]
            self.assertIn('prospective', recruit_statuses)
            self.assertIn('enrolled', recruit_statuses)
            
            cadet_statuses = [s['status'] for s in result['cadet_status_counts']]
            self.assertIn('active', cadet_statuses)
            self.assertIn('graduated', cadet_statuses)
    
    def test_system_statistics_route_unauthorized(self):
        """Test system statistics route without admin access"""
        # Test without login
        response = self.app.get('/admin/system-statistics')
        self.assertEqual(response.status_code, 302)  # Should redirect to login
        
        # Test with non-admin user (would need to implement session mocking)
        # This is a basic test - in a real scenario you'd mock the session
    
    def test_system_statistics_route_structure(self):
        """Test that system statistics route returns proper structure"""
        # This would require mocking the session to simulate admin login
        # For now, we'll test the helper functions directly
        with app.app_context():
            # Test that all helper functions work together
            db_size = get_database_size()
            record_counts = get_record_counts()
            system_performance = get_system_performance()
            user_activity = get_user_activity_stats()
            recruitment_stats = get_recruitment_stats()
            
            # All should return dictionaries
            self.assertIsInstance(db_size, dict)
            self.assertIsInstance(record_counts, dict)
            self.assertIsInstance(system_performance, dict)
            self.assertIsInstance(user_activity, dict)
            self.assertIsInstance(recruitment_stats, dict)
            
            # Calculate total records
            total_records = sum(record_counts.values())
            self.assertIsInstance(total_records, int)
            self.assertGreaterEqual(total_records, 0)

if __name__ == '__main__':
    unittest.main()
