#!/usr/bin/env python3
"""
Regression Tests for Database Cleanup Changes
Tests the removal of SQLite references and Neon PostgreSQL compatibility
"""

import os
import unittest
import tempfile
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestDatabaseCleanupRegression(unittest.TestCase):
    """Test that database cleanup changes work correctly"""
    
    def setUp(self):
        """Set up test environment"""
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv('env.local')
        
        # Import app after environment is loaded
        from app import app, db
        
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
    def test_no_sqlite_imports(self):
        """Test that sqlite3 and shutil imports are removed"""
        with open('app.py', 'r') as f:
            content = f.read()
            
        # Verify sqlite3 import is removed
        self.assertNotIn('import sqlite3', content)
        self.assertNotIn('import shutil', content)
        
        # Verify the comment about removal is present
        self.assertIn('# Removed sqlite3 import - using Neon PostgreSQL exclusively', content)
        
    def test_database_configuration(self):
        """Test that database configuration uses only DATABASE_URL"""
        with open('app.py', 'r') as f:
            content = f.read()
            
        # Verify old SQLite configuration is removed
        self.assertNotIn('sqlite:///', content)
        self.assertNotIn('BACKUP_DIR', content)
        self.assertNotIn('os.makedirs(BACKUP_DIR)', content)
        
        # Verify new Neon configuration is present
        self.assertIn("app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')", content)
        self.assertIn('# Database configuration - using Neon PostgreSQL exclusively', content)
        
    def test_backup_functions_use_neon_scheduler(self):
        """Test that backup functions import and use neon_backup_scheduler"""
        with open('app.py', 'r') as f:
            content = f.read()
            
        # Verify backup functions import neon_backup_scheduler
        self.assertIn('from neon_backup_scheduler import backup_database_neon', content)
        self.assertIn('from neon_backup_scheduler import list_backup_files', content)
        
        # Verify function calls use neon functions
        self.assertIn('return backup_database_neon(description)', content)
        self.assertIn('return list_backup_files()', content)
        
    def test_environment_variables(self):
        """Test that required environment variables are set"""
        self.assertIsNotNone(os.getenv('DATABASE_URL'))
        self.assertTrue(os.getenv('DATABASE_URL').startswith('postgres'))
        
    def test_neon_backup_scheduler_exists(self):
        """Test that neon_backup_scheduler.py exists and has required functions"""
        self.assertTrue(os.path.exists('neon_backup_scheduler.py'))
        
        with open('neon_backup_scheduler.py', 'r') as f:
            content = f.read()
            
        # Verify required functions exist
        self.assertIn('def backup_database_neon(', content)
        self.assertIn('def list_backup_files(', content)
        
    def test_app_imports_correctly(self):
        """Test that app.py imports correctly without SQLite dependencies"""
        try:
            from app import app, db
            self.assertIsNotNone(app)
            self.assertIsNotNone(db)
        except ImportError as e:
            self.fail(f"App import failed: {e}")
            
    def test_database_connection(self):
        """Test that database connection works with Neon PostgreSQL"""
        from app import app, db
        
        with app.app_context():
            try:
                # Test basic database connection
                result = db.session.execute('SELECT 1')
                self.assertEqual(result.scalar(), 1)
            except Exception as e:
                self.fail(f"Database connection failed: {e}")
                
    def test_backup_function_imports(self):
        """Test that backup functions can be imported and called"""
        from app import backup_database, get_backup_files
        
        # Test that functions exist and are callable
        self.assertTrue(callable(backup_database))
        self.assertTrue(callable(get_backup_files))
        
    @patch('app.backup_database_neon')
    def test_backup_database_calls_neon_function(self, mock_backup):
        """Test that backup_database calls the neon function"""
        from app import backup_database
        
        # Mock the return value
        mock_backup.return_value = ('test_backup.json', 'https://test.url')
        
        # Call the function
        result = backup_database("Test backup")
        
        # Verify neon function was called
        mock_backup.assert_called_once_with("Test backup")
        self.assertEqual(result, ('test_backup.json', 'https://test.url'))
        
    @patch('app.list_backup_files')
    def test_get_backup_files_calls_neon_function(self, mock_list):
        """Test that get_backup_files calls the neon function"""
        from app import get_backup_files
        
        # Mock the return value
        mock_list.return_value = [{'filename': 'test.json'}]
        
        # Call the function
        result = get_backup_files()
        
        # Verify neon function was called
        mock_list.assert_called_once()
        self.assertEqual(result, [{'filename': 'test.json'}])
        
    def test_restore_function_returns_false(self):
        """Test that restore_database returns False as expected"""
        from app import restore_database
        
        result = restore_database('test_file.json')
        self.assertFalse(result)
        
    def test_no_sqlite_fallback_logic(self):
        """Test that no SQLite fallback logic remains"""
        with open('app.py', 'r') as f:
            content = f.read()
            
        # Verify no SQLite fallback patterns
        self.assertNotIn('sqlite:///', content)
        self.assertNotIn('sqlite3.connect', content)
        self.assertNotIn('shutil.copy2', content)
        self.assertNotIn('os.path.join(os.getcwd()', content)
        
    def test_user_model_still_works(self):
        """Test that User model still works correctly"""
        from app import app, db, User
        
        with app.app_context():
            try:
                # Test basic User model operations
                user_count = User.query.count()
                self.assertIsInstance(user_count, int)
            except Exception as e:
                self.fail(f"User model test failed: {e}")
                
    def test_all_models_import_correctly(self):
        """Test that all database models import correctly"""
        from app import (
            User, PotentialRecruit, Cadet, UniversityContact, 
            RecruitmentEvent, ExternalLink, RecruitmentDocument, 
            ActivityLog, PasswordHistory
        )
        
        # Verify all models are imported
        models = [
            User, PotentialRecruit, Cadet, UniversityContact,
            RecruitmentEvent, ExternalLink, RecruitmentDocument,
            ActivityLog, PasswordHistory
        ]
        
        for model in models:
            self.assertIsNotNone(model)
            
    def test_flask_routes_still_work(self):
        """Test that basic Flask routes still work"""
        # Test that app can handle basic requests
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 302])  # 302 for redirect to login
        
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        
    def test_database_models_have_correct_columns(self):
        """Test that database models have expected columns"""
        from app import app, db, User
        
        with app.app_context():
            # Test that User model has expected columns
            user_columns = [column.name for column in User.__table__.columns]
            
            # Verify core columns exist
            expected_columns = ['id', 'username', 'password_hash', 'first_name', 'last_name']
            for column in expected_columns:
                self.assertIn(column, user_columns)
                
    def test_no_file_system_backup_references(self):
        """Test that no file system backup references remain"""
        with open('app.py', 'r') as f:
            content = f.read()
            
        # Verify no file system backup patterns
        self.assertNotIn('backup_path = os.path.join(BACKUP_DIR', content)
        self.assertNotIn('shutil.copy2(db_path, backup_path)', content)
        self.assertNotIn('os.path.getsize(backup_path)', content)
        self.assertNotIn('metadata_file = backup_path.replace', content)
        
    def test_environment_configuration_consistency(self):
        """Test that environment configuration is consistent"""
        # Verify DATABASE_URL is set and is PostgreSQL
        database_url = os.getenv('DATABASE_URL')
        self.assertIsNotNone(database_url)
        self.assertTrue(database_url.startswith('postgres'))
        
        # Verify no SQLite references in environment
        self.assertNotIn('sqlite', database_url.lower())
        
    def test_import_structure_integrity(self):
        """Test that import structure is intact after cleanup"""
        try:
            # Test all major imports
            from app import (
                app, db, User, PotentialRecruit, Cadet, 
                UniversityContact, RecruitmentEvent, ExternalLink,
                RecruitmentDocument, ActivityLog, PasswordHistory,
                backup_database, get_backup_files, restore_database
            )
            
            # Verify all imports succeeded
            self.assertIsNotNone(app)
            self.assertIsNotNone(db)
            
        except ImportError as e:
            self.fail(f"Import structure test failed: {e}")

if __name__ == '__main__':
    # Set up test environment
    os.environ['FLASK_ENV'] = 'testing'
    
    # Run tests
    unittest.main(verbosity=2)
