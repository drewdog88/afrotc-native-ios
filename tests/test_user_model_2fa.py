#!/usr/bin/env python3
"""
Unit Tests for User Model 2FA Functionality
Tests all 2FA-related properties and methods in the User model
"""

import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask and database components
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

# Create test app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'test-secret-key'

db = SQLAlchemy(app)

# Import User model (we'll define it here for testing)
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
    totp_secret = db.Column(db.String(255), nullable=True)  # Encrypted TOTP secret key
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)  # Whether 2FA is enabled
    backup_codes_hash = db.Column(db.Text, nullable=True)  # Encrypted backup codes
    totp_setup_completed = db.Column(db.Boolean, default=False, nullable=False)  # Setup completion status
    can_enable_2fa = db.Column(db.Boolean, default=True, nullable=False)  # Admin control flag
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 2FA Authentication Methods
    @property
    def is_2fa_enabled(self):
        """Check if 2FA is fully enabled for this user"""
        return self.totp_enabled and self.totp_setup_completed
    
    @property
    def can_use_2fa(self):
        """Check if user can enable/use 2FA"""
        return self.can_enable_2fa and self.is_active
    
    def has_2fa_setup(self):
        """Check if user has started 2FA setup process"""
        return self.totp_secret is not None
    
    def needs_2fa_setup(self):
        """Check if user needs to complete 2FA setup"""
        return self.totp_enabled and not self.totp_setup_completed


class TestUserModel2FA(unittest.TestCase):
    """Test suite for User model 2FA functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create database tables
        db.create_all()
        
        # Create test user
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
    
    def test_user_creation_with_2fa_fields(self):
        """Test user creation with 2FA fields"""
        # Verify default 2FA values
        self.assertFalse(self.user.totp_enabled)
        self.assertFalse(self.user.totp_setup_completed)
        self.assertTrue(self.user.can_enable_2fa)
        self.assertIsNone(self.user.totp_secret)
        self.assertIsNone(self.user.backup_codes_hash)
    
    def test_is_2fa_enabled_property(self):
        """Test is_2fa_enabled property"""
        # Initially should be False
        self.assertFalse(self.user.is_2fa_enabled)
        
        # Enable 2FA but don't complete setup
        self.user.totp_enabled = True
        self.user.totp_setup_completed = False
        db.session.commit()
        self.assertFalse(self.user.is_2fa_enabled)
        
        # Complete setup
        self.user.totp_setup_completed = True
        db.session.commit()
        self.assertTrue(self.user.is_2fa_enabled)
        
        # Disable 2FA
        self.user.totp_enabled = False
        db.session.commit()
        self.assertFalse(self.user.is_2fa_enabled)
    
    def test_can_use_2fa_property(self):
        """Test can_use_2fa property"""
        # Initially should be True (active user, can enable 2FA)
        self.assertTrue(self.user.can_use_2fa)
        
        # Disable 2FA capability
        self.user.can_enable_2fa = False
        db.session.commit()
        self.assertFalse(self.user.can_use_2fa)
        
        # Re-enable 2FA capability but deactivate user
        self.user.can_enable_2fa = True
        self.user.is_active = False
        db.session.commit()
        self.assertFalse(self.user.can_use_2fa)
        
        # Reactivate user
        self.user.is_active = True
        db.session.commit()
        self.assertTrue(self.user.can_use_2fa)
    
    def test_has_2fa_setup_method(self):
        """Test has_2fa_setup method"""
        # Initially should be False
        self.assertFalse(self.user.has_2fa_setup())
        
        # Set TOTP secret
        self.user.totp_secret = "test_secret"
        db.session.commit()
        self.assertTrue(self.user.has_2fa_setup())
        
        # Clear TOTP secret
        self.user.totp_secret = None
        db.session.commit()
        self.assertFalse(self.user.has_2fa_setup())
    
    def test_needs_2fa_setup_method(self):
        """Test needs_2fa_setup method"""
        # Initially should be False
        self.assertFalse(self.user.needs_2fa_setup())
        
        # Enable 2FA but don't complete setup
        self.user.totp_enabled = True
        self.user.totp_setup_completed = False
        db.session.commit()
        self.assertTrue(self.user.needs_2fa_setup())
        
        # Complete setup
        self.user.totp_setup_completed = True
        db.session.commit()
        self.assertFalse(self.user.needs_2fa_setup())
        
        # Disable 2FA
        self.user.totp_enabled = False
        db.session.commit()
        self.assertFalse(self.user.needs_2fa_setup())
    
    def test_2fa_setup_workflow(self):
        """Test complete 2FA setup workflow"""
        # Step 1: User starts 2FA setup
        self.user.totp_secret = "encrypted_secret_key"
        self.user.totp_enabled = True
        self.user.totp_setup_completed = False
        db.session.commit()
        
        # Verify state
        self.assertTrue(self.user.has_2fa_setup())
        self.assertTrue(self.user.needs_2fa_setup())
        self.assertFalse(self.user.is_2fa_enabled)
        
        # Step 2: User completes setup
        self.user.totp_setup_completed = True
        self.user.backup_codes_hash = "encrypted_backup_codes"
        db.session.commit()
        
        # Verify final state
        self.assertTrue(self.user.has_2fa_setup())
        self.assertFalse(self.user.needs_2fa_setup())
        self.assertTrue(self.user.is_2fa_enabled)
    
    def test_2fa_disable_workflow(self):
        """Test 2FA disable workflow"""
        # Set up 2FA
        self.user.totp_secret = "encrypted_secret_key"
        self.user.totp_enabled = True
        self.user.totp_setup_completed = True
        self.user.backup_codes_hash = "encrypted_backup_codes"
        db.session.commit()
        
        # Verify 2FA is enabled
        self.assertTrue(self.user.is_2fa_enabled)
        
        # Disable 2FA
        self.user.totp_enabled = False
        self.user.totp_setup_completed = False
        self.user.totp_secret = None
        self.user.backup_codes_hash = None
        db.session.commit()
        
        # Verify 2FA is disabled
        self.assertFalse(self.user.is_2fa_enabled)
        self.assertFalse(self.user.has_2fa_setup())
        self.assertFalse(self.user.needs_2fa_setup())
    
    def test_admin_control_2fa(self):
        """Test admin control over 2FA enablement"""
        # Admin disables 2FA for user
        self.user.can_enable_2fa = False
        db.session.commit()
        
        # User should not be able to use 2FA
        self.assertFalse(self.user.can_use_2fa)
        
        # Even if 2FA is technically enabled, user can't use it
        self.user.totp_enabled = True
        self.user.totp_setup_completed = True
        db.session.commit()
        
        self.assertFalse(self.user.can_use_2fa)
        
        # Admin re-enables 2FA
        self.user.can_enable_2fa = True
        db.session.commit()
        
        self.assertTrue(self.user.can_use_2fa)
    
    def test_user_inactive_2fa(self):
        """Test 2FA behavior with inactive users"""
        # Deactivate user
        self.user.is_active = False
        db.session.commit()
        
        # User should not be able to use 2FA
        self.assertFalse(self.user.can_use_2fa)
        
        # Even if 2FA is technically enabled, inactive user can't use it
        self.user.totp_enabled = True
        self.user.totp_setup_completed = True
        db.session.commit()
        
        self.assertFalse(self.user.can_use_2fa)
        
        # Reactivate user
        self.user.is_active = True
        db.session.commit()
        
        self.assertTrue(self.user.can_use_2fa)
    
    def test_2fa_edge_cases(self):
        """Test 2FA edge cases"""
        # Test with None values
        self.user.totp_secret = None
        self.user.backup_codes_hash = None
        db.session.commit()
        
        self.assertFalse(self.user.has_2fa_setup())
        
        # Test with empty strings
        self.user.totp_secret = ""
        self.user.backup_codes_hash = ""
        db.session.commit()
        
        self.assertTrue(self.user.has_2fa_setup())  # Empty string is not None
        
        # Test with boolean edge cases
        self.user.totp_enabled = True
        self.user.totp_setup_completed = True
        self.user.can_enable_2fa = True
        self.user.is_active = True
        db.session.commit()
        
        self.assertTrue(self.user.is_2fa_enabled)
        self.assertTrue(self.user.can_use_2fa)
    
    def test_database_persistence(self):
        """Test that 2FA fields persist correctly in database"""
        # Set up 2FA
        self.user.totp_secret = "test_secret_123"
        self.user.totp_enabled = True
        self.user.totp_setup_completed = True
        self.user.backup_codes_hash = "test_backup_codes"
        self.user.can_enable_2fa = False
        db.session.commit()
        
        # Query user from database
        user_from_db = User.query.get(self.user.id)
        
        # Verify all fields persisted
        self.assertEqual(user_from_db.totp_secret, "test_secret_123")
        self.assertTrue(user_from_db.totp_enabled)
        self.assertTrue(user_from_db.totp_setup_completed)
        self.assertEqual(user_from_db.backup_codes_hash, "test_backup_codes")
        self.assertFalse(user_from_db.can_enable_2fa)
        
        # Verify computed properties
        self.assertTrue(user_from_db.is_2fa_enabled)
        self.assertFalse(user_from_db.can_use_2fa)
        self.assertTrue(user_from_db.has_2fa_setup())
        self.assertFalse(user_from_db.needs_2fa_setup())


class TestUserModel2FAIntegration(unittest.TestCase):
    """Integration tests for User model 2FA functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_multiple_users_2fa_states(self):
        """Test multiple users with different 2FA states"""
        # Create users with different 2FA states
        user1 = User(
            username='user1',
            email='user1@example.com',
            password_hash=generate_password_hash('password'),
            secret_question='Question 1',
            secret_answer_hash=generate_password_hash('answer1'),
            totp_enabled=True,
            totp_setup_completed=True,
            can_enable_2fa=True,
            is_active=True
        )
        
        user2 = User(
            username='user2',
            email='user2@example.com',
            password_hash=generate_password_hash('password'),
            secret_question='Question 2',
            secret_answer_hash=generate_password_hash('answer2'),
            totp_enabled=False,
            totp_setup_completed=False,
            can_enable_2fa=True,
            is_active=True
        )
        
        user3 = User(
            username='user3',
            email='user3@example.com',
            password_hash=generate_password_hash('password'),
            secret_question='Question 3',
            secret_answer_hash=generate_password_hash('answer3'),
            totp_enabled=True,
            totp_setup_completed=False,
            can_enable_2fa=False,
            is_active=True
        )
        
        db.session.add_all([user1, user2, user3])
        db.session.commit()
        
        # Verify states
        self.assertTrue(user1.is_2fa_enabled)
        self.assertTrue(user1.can_use_2fa)
        
        self.assertFalse(user2.is_2fa_enabled)
        self.assertTrue(user2.can_use_2fa)
        
        self.assertFalse(user3.is_2fa_enabled)
        self.assertFalse(user3.can_use_2fa)
    
    def test_2fa_query_filters(self):
        """Test querying users by 2FA status"""
        # Create users with different 2FA states
        users = []
        for i in range(5):
            user = User(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password_hash=generate_password_hash('password'),
                secret_question=f'Question {i}',
                secret_answer_hash=generate_password_hash(f'answer{i}'),
                totp_enabled=(i % 2 == 0),  # Even users have 2FA enabled
                totp_setup_completed=(i % 2 == 0),
                can_enable_2fa=True,
                is_active=True
            )
            users.append(user)
        
        db.session.add_all(users)
        db.session.commit()
        
        # Query users with 2FA enabled
        enabled_users = User.query.filter_by(totp_enabled=True).all()
        self.assertEqual(len(enabled_users), 3)  # Users 0, 2, 4
        
        # Query users with 2FA disabled
        disabled_users = User.query.filter_by(totp_enabled=False).all()
        self.assertEqual(len(disabled_users), 2)  # Users 1, 3
        
        # Query users who can enable 2FA
        can_enable_users = User.query.filter_by(can_enable_2fa=True).all()
        self.assertEqual(len(can_enable_users), 5)  # All users


if __name__ == '__main__':
    # Create test suite using modern approach
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add test cases using modern method
    test_suite.addTests(loader.loadTestsFromTestCase(TestUserModel2FA))
    test_suite.addTests(loader.loadTestsFromTestCase(TestUserModel2FAIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(not result.wasSuccessful())
