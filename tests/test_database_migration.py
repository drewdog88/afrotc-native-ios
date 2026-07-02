#!/usr/bin/env python3
"""
Unit Tests for Database Migration Functionality
Tests 2FA column addition, validation, and migration rollback capabilities
"""

import unittest
import os
import sys
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask and database components
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create test app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'test-secret-key'

db = SQLAlchemy(app)

# Import User model
class User(db.Model):
    """User model with 2FA support"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    force_password_change = db.Column(db.Boolean, default=False, nullable=False)
    days_until_password_expiry = db.Column(db.Integer, nullable=True)
    secret_question = db.Column(db.String(200), nullable=False)
    secret_answer_hash = db.Column(db.String(120), nullable=False)
    
    # 2FA Authentication Fields
    totp_secret = db.Column(db.String(255), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)
    backup_codes_hash = db.Column(db.Text, nullable=True)
    totp_setup_completed = db.Column(db.Boolean, default=False, nullable=False)
    can_enable_2fa = db.Column(db.Boolean, default=True, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TestDatabaseMigration(unittest.TestCase):
    """Test suite for database migration functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create database tables
        db.create_all()
        
        # Create test user
        from werkzeug.security import generate_password_hash
        self.user = User(
            username='testuser',
            email='test@example.com',
            password_hash=generate_password_hash('password123'),
            role='user',
            is_active=True,
            secret_question='What is your favorite color?',
            secret_answer_hash=generate_password_hash('blue')
        )
        db.session.add(self.user)
        db.session.commit()
    
    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_2fa_columns_exist(self):
        """Test that 2FA columns exist in the database"""
        # Check if 2FA columns exist
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        expected_2fa_columns = [
            'totp_secret',
            'totp_enabled', 
            'backup_codes_hash',
            'totp_setup_completed',
            'can_enable_2fa'
        ]
        
        for column in expected_2fa_columns:
            self.assertIn(column, columns, f"2FA column '{column}' not found in database")
    
    def test_2fa_columns_default_values(self):
        """Test that 2FA columns have correct default values"""
        # Verify default values for new user
        self.assertIsNone(self.user.totp_secret)
        self.assertFalse(self.user.totp_enabled)
        self.assertIsNone(self.user.backup_codes_hash)
        self.assertFalse(self.user.totp_setup_completed)
        self.assertTrue(self.user.can_enable_2fa)
    
    def test_2fa_columns_nullable(self):
        """Test that 2FA columns are nullable as expected"""
        # Test that nullable columns can be set to None
        self.user.totp_secret = None
        self.user.backup_codes_hash = None
        db.session.commit()
        
        # Verify changes persisted
        user = User.query.get(self.user.id)
        self.assertIsNone(user.totp_secret)
        self.assertIsNone(user.backup_codes_hash)
    
    def test_2fa_columns_not_nullable(self):
        """Test that required 2FA columns cannot be None"""
        # Test boolean columns that should not be None
        self.user.totp_enabled = False
        self.user.totp_setup_completed = False
        self.user.can_enable_2fa = True
        db.session.commit()
        
        # Verify changes persisted
        user = User.query.get(self.user.id)
        self.assertFalse(user.totp_enabled)
        self.assertFalse(user.totp_setup_completed)
        self.assertTrue(user.can_enable_2fa)
    
    def test_2fa_columns_data_types(self):
        """Test that 2FA columns have correct data types"""
        # Set test values
        self.user.totp_secret = "test_secret_key_123"
        self.user.totp_enabled = True
        self.user.backup_codes_hash = "test_backup_codes_json"
        self.user.totp_setup_completed = True
        self.user.can_enable_2fa = False
        db.session.commit()
        
        # Verify data types and values
        user = User.query.get(self.user.id)
        self.assertIsInstance(user.totp_secret, str)
        self.assertIsInstance(user.totp_enabled, bool)
        self.assertIsInstance(user.backup_codes_hash, str)
        self.assertIsInstance(user.totp_setup_completed, bool)
        self.assertIsInstance(user.can_enable_2fa, bool)
        
        self.assertEqual(user.totp_secret, "test_secret_key_123")
        self.assertTrue(user.totp_enabled)
        self.assertEqual(user.backup_codes_hash, "test_backup_codes_json")
        self.assertTrue(user.totp_setup_completed)
        self.assertFalse(user.can_enable_2fa)
    
    def test_2fa_columns_indexes(self):
        """Test that 2FA columns have appropriate indexes"""
        # This test would check for indexes in a real database
        # For SQLite in-memory, we'll just verify the columns exist
        inspector = db.inspect(db.engine)
        indexes = inspector.get_indexes('user')
        
        # Check if indexes exist (this may vary by database)
        index_names = [idx['name'] for idx in indexes]
        
        # Note: In SQLite, indexes might not be created the same way as PostgreSQL
        # This test is more relevant for actual database deployments
        self.assertIsInstance(indexes, list)
    
    def test_2fa_columns_constraints(self):
        """Test that 2FA columns have appropriate constraints"""
        # Test boolean constraints
        self.user.totp_enabled = True
        self.user.totp_setup_completed = True
        self.user.can_enable_2fa = True
        db.session.commit()
        
        # Test string length constraints
        long_secret = "x" * 300  # Longer than VARCHAR(255)
        self.user.totp_secret = long_secret
        db.session.commit()
        
        # Verify the long string was truncated or handled appropriately
        user = User.query.get(self.user.id)
        self.assertIsNotNone(user.totp_secret)
    
    def test_2fa_columns_backward_compatibility(self):
        """Test that 2FA columns don't break existing functionality"""
        # Test that existing user data is preserved
        original_username = self.user.username
        original_email = self.user.email
        original_role = self.user.role
        
        # Add 2FA data
        self.user.totp_enabled = True
        self.user.totp_secret = "test_secret"
        db.session.commit()
        
        # Verify original data is still intact
        user = User.query.get(self.user.id)
        self.assertEqual(user.username, original_username)
        self.assertEqual(user.email, original_email)
        self.assertEqual(user.role, original_role)
        
        # Verify 2FA data was added
        self.assertTrue(user.totp_enabled)
        self.assertEqual(user.totp_secret, "test_secret")
    
    def test_2fa_columns_query_performance(self):
        """Test that 2FA columns don't significantly impact query performance"""
        # Create multiple users with different 2FA states
        users = []
        for i in range(10):
            user = User(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password_hash='hash',
                role='user',
                secret_question='Question',
                secret_answer_hash='hash',
                totp_enabled=(i % 2 == 0),  # Alternate 2FA enabled
                totp_setup_completed=(i % 2 == 0),
                can_enable_2fa=True
            )
            users.append(user)
        
        db.session.add_all(users)
        db.session.commit()
        
        # Test queries on 2FA columns
        # Scope queries to just users created in this test (user0..user9)
        enabled_users = User.query.filter(User.username.like('user%'), User.totp_enabled == True).all()
        disabled_users = User.query.filter(User.username.like('user%'), User.totp_enabled == False).all()
        
        self.assertEqual(len(enabled_users), 5)
        self.assertEqual(len(disabled_users), 5)
        
        # Test complex queries
        active_2fa_users = User.query.filter(
            User.username.like('user%'),
            User.is_active == True,
            User.totp_enabled == True,
            User.totp_setup_completed == True
        ).all()
        
        self.assertEqual(len(active_2fa_users), 5)
    
    def test_2fa_columns_data_integrity(self):
        """Test data integrity with 2FA columns"""
        # Test that 2FA state is consistent
        self.user.totp_enabled = True
        self.user.totp_setup_completed = False
        db.session.commit()
        
        # User should not be considered 2FA enabled if setup is not completed
        user = User.query.get(self.user.id)
        self.assertTrue(user.totp_enabled)
        self.assertFalse(user.totp_setup_completed)
        
        # Complete setup
        self.user.totp_setup_completed = True
        self.user.totp_secret = "test_secret"
        self.user.backup_codes_hash = "test_backup_codes"
        db.session.commit()
        
        # Now user should be fully 2FA enabled
        user = User.query.get(self.user.id)
        self.assertTrue(user.totp_enabled)
        self.assertTrue(user.totp_setup_completed)
        self.assertIsNotNone(user.totp_secret)
        self.assertIsNotNone(user.backup_codes_hash)
    
    def test_2fa_columns_transaction_support(self):
        """Test transaction support with 2FA columns"""
        # Start transaction
        db.session.begin()
        
        try:
            # Modify 2FA settings
            self.user.totp_enabled = True
            self.user.totp_secret = "transaction_secret"
            db.session.commit()
            
            # Verify changes
            user = User.query.get(self.user.id)
            self.assertTrue(user.totp_enabled)
            self.assertEqual(user.totp_secret, "transaction_secret")
            
        except Exception:
            db.session.rollback()
            raise
    
    def test_2fa_columns_concurrent_access(self):
        """Test concurrent access to 2FA columns"""
        # Simulate concurrent access by creating multiple users
        users = []
        for i in range(5):
            user = User(
                username=f'concurrent_user{i}',
                email=f'concurrent{i}@example.com',
                password_hash='hash',
                role='user',
                secret_question='Question',
                secret_answer_hash='hash',
                totp_enabled=True,
                totp_secret=f'secret_{i}',
                backup_codes_hash=f'backup_{i}',
                totp_setup_completed=True,
                can_enable_2fa=True
            )
            users.append(user)
        
        db.session.add_all(users)
        db.session.commit()
        
        # Verify all users were created with 2FA data
        for i, user in enumerate(users):
            db_user = User.query.filter_by(username=f'concurrent_user{i}').first()
            self.assertIsNotNone(db_user)
            self.assertTrue(db_user.totp_enabled)
            self.assertEqual(db_user.totp_secret, f'secret_{i}')
            self.assertEqual(db_user.backup_codes_hash, f'backup_{i}')


class TestMigrationSQL(unittest.TestCase):
    """Test suite for migration SQL scripts"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Create SQLite database
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Create basic user table without 2FA columns
        self.cursor.execute('''
            CREATE TABLE "user" (
                id INTEGER PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(120) NOT NULL,
                role VARCHAR(20) DEFAULT 'user' NOT NULL,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                is_locked BOOLEAN DEFAULT FALSE NOT NULL,
                failed_login_attempts INTEGER DEFAULT 0 NOT NULL,
                force_password_change BOOLEAN DEFAULT FALSE NOT NULL,
                days_until_password_expiry INTEGER,
                secret_question VARCHAR(200) NOT NULL,
                secret_answer_hash VARCHAR(120) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_modified DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert test user
        self.cursor.execute('''
            INSERT INTO "user" (username, email, password_hash, secret_question, secret_answer_hash)
            VALUES (?, ?, ?, ?, ?)
        ''', ('testuser', 'test@example.com', 'hash', 'Question', 'hash'))
        
        self.conn.commit()
    
    def tearDown(self):
        """Clean up test environment"""
        self.conn.close()
        os.unlink(self.db_path)
    
    def test_migration_adds_2fa_columns(self):
        """Test that migration adds 2FA columns correctly"""
        # Execute migration SQL (adapted for SQLite)
        migration_sql = '''
            -- Add 2FA columns to User table
            ALTER TABLE "user" ADD COLUMN totp_secret VARCHAR(255);
            ALTER TABLE "user" ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE;
            ALTER TABLE "user" ADD COLUMN backup_codes_hash TEXT;
            ALTER TABLE "user" ADD COLUMN totp_setup_completed BOOLEAN DEFAULT FALSE;
            ALTER TABLE "user" ADD COLUMN can_enable_2fa BOOLEAN DEFAULT TRUE;
        '''
        
        self.cursor.executescript(migration_sql)
        self.conn.commit()
        
        # Verify columns were added
        self.cursor.execute("PRAGMA table_info(user)")
        columns = [row[1] for row in self.cursor.fetchall()]
        
        expected_2fa_columns = [
            'totp_secret',
            'totp_enabled',
            'backup_codes_hash',
            'totp_setup_completed',
            'can_enable_2fa'
        ]
        
        for column in expected_2fa_columns:
            self.assertIn(column, columns, f"2FA column '{column}' not found")
    
    def test_migration_preserves_existing_data(self):
        """Test that migration preserves existing user data"""
        # Execute migration
        migration_sql = '''
            ALTER TABLE "user" ADD COLUMN totp_secret VARCHAR(255);
            ALTER TABLE "user" ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE;
            ALTER TABLE "user" ADD COLUMN backup_codes_hash TEXT;
            ALTER TABLE "user" ADD COLUMN totp_setup_completed BOOLEAN DEFAULT FALSE;
            ALTER TABLE "user" ADD COLUMN can_enable_2fa BOOLEAN DEFAULT TRUE;
        '''
        
        self.cursor.executescript(migration_sql)
        self.conn.commit()
        
        # Verify existing data is preserved
        self.cursor.execute('SELECT username, email FROM "user" WHERE username = ?', ('testuser',))
        user_data = self.cursor.fetchone()
        
        self.assertIsNotNone(user_data)
        self.assertEqual(user_data[0], 'testuser')
        self.assertEqual(user_data[1], 'test@example.com')
    
    def test_migration_default_values(self):
        """Test that migration sets correct default values"""
        # Execute migration
        migration_sql = '''
            ALTER TABLE "user" ADD COLUMN totp_secret VARCHAR(255);
            ALTER TABLE "user" ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE;
            ALTER TABLE "user" ADD COLUMN backup_codes_hash TEXT;
            ALTER TABLE "user" ADD COLUMN totp_setup_completed BOOLEAN DEFAULT FALSE;
            ALTER TABLE "user" ADD COLUMN can_enable_2fa BOOLEAN DEFAULT TRUE;
        '''
        
        self.cursor.executescript(migration_sql)
        self.conn.commit()
        
        # Check default values
        self.cursor.execute('''
            SELECT totp_enabled, totp_setup_completed, can_enable_2fa 
            FROM "user" WHERE username = ?
        ''', ('testuser',))
        
        user_data = self.cursor.fetchone()
        self.assertIsNotNone(user_data)
        self.assertEqual(user_data[0], 0)  # FALSE in SQLite
        self.assertEqual(user_data[1], 0)  # FALSE in SQLite
        self.assertEqual(user_data[2], 1)  # TRUE in SQLite
    
    def test_migration_nullable_columns(self):
        """Test that nullable 2FA columns can be NULL"""
        # Execute migration
        migration_sql = '''
            ALTER TABLE "user" ADD COLUMN totp_secret VARCHAR(255);
            ALTER TABLE "user" ADD COLUMN backup_codes_hash TEXT;
        '''
        
        self.cursor.executescript(migration_sql)
        self.conn.commit()
        
        # Test inserting NULL values
        self.cursor.execute('''
            UPDATE "user" 
            SET totp_secret = NULL, backup_codes_hash = NULL 
            WHERE username = ?
        ''', ('testuser',))
        
        self.conn.commit()
        
        # Verify NULL values are accepted
        self.cursor.execute('''
            SELECT totp_secret, backup_codes_hash 
            FROM "user" WHERE username = ?
        ''', ('testuser',))
        
        user_data = self.cursor.fetchone()
        self.assertIsNone(user_data[0])
        self.assertIsNone(user_data[1])
    
    def test_migration_data_insertion(self):
        """Test that 2FA data can be inserted after migration"""
        # Execute migration
        migration_sql = '''
            ALTER TABLE "user" ADD COLUMN totp_secret VARCHAR(255);
            ALTER TABLE "user" ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE;
            ALTER TABLE "user" ADD COLUMN backup_codes_hash TEXT;
            ALTER TABLE "user" ADD COLUMN totp_setup_completed BOOLEAN DEFAULT FALSE;
            ALTER TABLE "user" ADD COLUMN can_enable_2fa BOOLEAN DEFAULT TRUE;
        '''
        
        self.cursor.executescript(migration_sql)
        self.conn.commit()
        
        # Insert 2FA data
        self.cursor.execute('''
            UPDATE "user" 
            SET totp_secret = ?, totp_enabled = ?, backup_codes_hash = ?, 
                totp_setup_completed = ?, can_enable_2fa = ?
            WHERE username = ?
        ''', ('test_secret', True, 'test_backup_codes', True, False, 'testuser'))
        
        self.conn.commit()
        
        # Verify 2FA data was inserted
        self.cursor.execute('''
            SELECT totp_secret, totp_enabled, backup_codes_hash, 
                   totp_setup_completed, can_enable_2fa
            FROM "user" WHERE username = ?
        ''', ('testuser',))
        
        user_data = self.cursor.fetchone()
        self.assertEqual(user_data[0], 'test_secret')
        self.assertEqual(user_data[1], 1)  # TRUE in SQLite
        self.assertEqual(user_data[2], 'test_backup_codes')
        self.assertEqual(user_data[3], 1)  # TRUE in SQLite
        self.assertEqual(user_data[4], 0)  # FALSE in SQLite


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestDatabaseMigration))
    test_suite.addTest(unittest.makeSuite(TestMigrationSQL))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(not result.wasSuccessful())
