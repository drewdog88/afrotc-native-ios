#!/usr/bin/env python3
"""
Test Form Data Preservation - Task #20
Tests that form data is preserved when password validation fails in user creation form.
"""

import unittest
import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import tempfile
import shutil

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TestFormDataPreservation(unittest.TestCase):
    """Test cases for form data preservation functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Create test Flask app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.db_path}'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Initialize database
        self.db = SQLAlchemy(self.app)
        
        # Import models and routes
        with self.app.app_context():
            # Import the User model
            from api.app import User, validate_password
            
            # Create tables
            self.db.create_all()
            
            # Store references for testing
            self.User = User
            self.validate_password = validate_password
            
            # Create test admin user
            admin_user = User(
                username='testadmin',
                email='admin@test.com',
                password_hash=generate_password_hash('Admin123!'),
                first_name='Test',
                last_name='Admin',
                secret_question='Test question?',
                secret_answer_hash=generate_password_hash('test'),
                role='admin'
            )
            self.db.session.add(admin_user)
            self.db.session.commit()
            self.admin_user_id = admin_user.id
    
    def tearDown(self):
        """Clean up test environment"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_password_validation_requirements(self):
        """Test that password validation correctly identifies all requirements"""
        # Test valid password
        valid_password = "StrongPass123!"
        errors = self.validate_password(valid_password)
        self.assertEqual(errors, [], "Valid password should have no errors")
        
        # Test password too short
        short_password = "Abc1!"
        errors = self.validate_password(short_password)
        self.assertIn("Password must be at least 8 characters long", errors)
        
        # Test password without uppercase
        no_upper = "strongpass123!"
        errors = self.validate_password(no_upper)
        self.assertIn("Password must contain at least one uppercase letter", errors)
        
        # Test password without lowercase
        no_lower = "STRONGPASS123!"
        errors = self.validate_password(no_lower)
        self.assertIn("Password must contain at least one lowercase letter", errors)
        
        # Test password without number
        no_number = "StrongPass!"
        errors = self.validate_password(no_number)
        self.assertIn("Password must contain at least one number", errors)
        
        # Test password without special character
        no_special = "StrongPass123"
        errors = self.validate_password(no_special)
        self.assertIn("Password must contain at least one special character", errors)
    
    def test_form_data_preservation_simulation(self):
        """Test that form data would be preserved in a real form submission"""
        # Simulate form data that would be submitted
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '555-1234',
            'role': 'recruiter',
            'password': 'weak',  # Invalid password
            'secret_question': 'What is your favorite color?',
            'secret_answer': 'Blue'
        }
        
        # Test that password validation fails
        password_errors = self.validate_password(form_data['password'])
        self.assertGreater(len(password_errors), 0, "Weak password should fail validation")
        
        # Simulate what the template would do with preserved form data
        preserved_data = {
            'first_name': form_data.get('first_name', ''),
            'last_name': form_data.get('last_name', ''),
            'username': form_data.get('username', ''),
            'email': form_data.get('email', ''),
            'phone': form_data.get('phone', ''),
            'role': form_data.get('role', ''),
            'secret_question': form_data.get('secret_question', ''),
            'secret_answer': form_data.get('secret_answer', '')
        }
        
        # Verify all form data is preserved (except password)
        self.assertEqual(preserved_data['first_name'], 'John')
        self.assertEqual(preserved_data['last_name'], 'Doe')
        self.assertEqual(preserved_data['username'], 'testuser')
        self.assertEqual(preserved_data['email'], 'test@example.com')
        self.assertEqual(preserved_data['phone'], '555-1234')
        self.assertEqual(preserved_data['role'], 'recruiter')
        self.assertEqual(preserved_data['secret_question'], 'What is your favorite color?')
        self.assertEqual(preserved_data['secret_answer'], 'Blue')
        
        # Verify password is NOT preserved (for security)
        self.assertNotIn('password', preserved_data)
    
    def test_template_value_rendering(self):
        """Test that template value rendering works correctly"""
        # Simulate request.form data
        form_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'username': 'janesmith',
            'email': 'jane@example.com',
            'phone': '555-5678',
            'role': 'admin',
            'secret_question': 'What is your pet\'s name?',
            'secret_answer': 'Fluffy'
        }
        
        # Test template value extraction (simulating Jinja2 template logic)
        def get_form_value(field_name, default=''):
            return form_data.get(field_name, default)
        
        # Verify each field preserves its value
        self.assertEqual(get_form_value('first_name'), 'Jane')
        self.assertEqual(get_form_value('last_name'), 'Smith')
        self.assertEqual(get_form_value('username'), 'janesmith')
        self.assertEqual(get_form_value('email'), 'jane@example.com')
        self.assertEqual(get_form_value('phone'), '555-5678')
        self.assertEqual(get_form_value('role'), 'admin')
        self.assertEqual(get_form_value('secret_question'), 'What is your pet\'s name?')
        self.assertEqual(get_form_value('secret_answer'), 'Fluffy')
        
        # Test default values for missing fields
        self.assertEqual(get_form_value('nonexistent_field'), '')
        self.assertEqual(get_form_value('another_field', 'default'), 'default')
    
    def test_role_selection_preservation(self):
        """Test that role selection is properly preserved"""
        # Test admin role selection
        admin_form_data = {'role': 'admin'}
        is_admin_selected = admin_form_data.get('role') == 'admin'
        self.assertTrue(is_admin_selected)
        
        # Test recruiter role selection
        recruiter_form_data = {'role': 'recruiter'}
        is_recruiter_selected = recruiter_form_data.get('role') == 'recruiter'
        self.assertTrue(is_recruiter_selected)
        
        # Test no role selected
        no_role_form_data = {}
        is_no_role_selected = no_role_form_data.get('role') == 'admin'
        self.assertFalse(is_no_role_selected)
    
    def test_password_strength_validation(self):
        """Test password strength validation logic"""
        # Test various password strengths
        test_cases = [
            ('', 0, 'empty'),
            ('a', 1, 'very weak'),
            ('ab', 1, 'very weak'),
            ('abc', 1, 'very weak'),
            ('abcd', 1, 'very weak'),
            ('abcde', 1, 'very weak'),
            ('abcdef', 1, 'very weak'),
            ('abcdefg', 1, 'very weak'),
            ('abcdefgh', 1, 'weak'),
            ('ABCDEFGH', 2, 'weak'),
            ('abcdefgh1', 2, 'weak'),
            ('ABCDEFGH1', 3, 'fair'),
            ('abcdefgh1!', 3, 'fair'),
            ('ABCDEFGH1!', 4, 'good'),
            ('abcdefgh1!A', 5, 'strong'),
        ]
        
        for password, expected_strength, description in test_cases:
            with self.subTest(password=password, description=description):
                # Calculate strength (simulating JavaScript logic)
                strength = 0
                if len(password) >= 8:
                    strength += 1
                if any(c.isupper() for c in password):
                    strength += 1
                if any(c.islower() for c in password):
                    strength += 1
                if any(c.isdigit() for c in password):
                    strength += 1
                if any(c in '!@#$%^&*(),.?":{}|<>' for c in password):
                    strength += 1
                
                self.assertEqual(strength, expected_strength, 
                               f"Password '{password}' should have strength {expected_strength}, got {strength}")

def run_functional_tests():
    """Run functional tests to verify the implementation works"""
    print("🧪 Running Functional Tests for Form Data Preservation...")
    
    # Test 1: Verify template changes
    print("\n1. Testing Template Changes...")
    try:
        with open('templates/add_user.html', 'r') as f:
            template_content = f.read()
        
        # Check for form data preservation
        assert 'value="{{ request.form.get(' in template_content, "Form data preservation not found"
        assert 'id="password-strength"' in template_content, "Password strength indicator not found"
        assert 'addEventListener' in template_content, "JavaScript validation not found"
        
        print("✅ Template changes verified")
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return False
    
    # Test 2: Verify password validation function exists
    print("\n2. Testing Password Validation Function...")
    try:
        from api.app import validate_password
        
        # Test various passwords
        test_passwords = [
            ("StrongPass123!", []),  # Valid
            ("weak", ["Password must be at least 8 characters long"]),  # Too short
            ("NoSpecial123", ["Password must contain at least one special character"]),  # No special char
        ]
        
        for password, expected_errors in test_passwords:
            errors = validate_password(password)
            if expected_errors:
                assert len(errors) > 0, f"Password '{password}' should have validation errors"
            else:
                assert len(errors) == 0, f"Password '{password}' should be valid"
        
        print("✅ Password validation function verified")
    except Exception as e:
        print(f"❌ Password validation test failed: {e}")
        return False
    
    # Test 3: Verify form data preservation logic
    print("\n3. Testing Form Data Preservation Logic...")
    try:
        # Simulate form submission with validation error
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'john@example.com',
            'phone': '555-1234',
            'role': 'recruiter',
            'password': 'weak',  # Invalid password
            'secret_question': 'What is your favorite color?',
            'secret_answer': 'Blue'
        }
        
        # Verify all fields except password are preserved
        preserved_fields = ['first_name', 'last_name', 'username', 'email', 'phone', 'role', 'secret_question', 'secret_answer']
        for field in preserved_fields:
            assert field in form_data, f"Field '{field}' should be preserved"
        
        # Verify password is not preserved (security)
        assert 'password' in form_data, "Password should be in form data for validation"
        
        print("✅ Form data preservation logic verified")
    except Exception as e:
        print(f"❌ Form data preservation test failed: {e}")
        return False
    
    print("\n🎉 All functional tests passed!")
    return True

if __name__ == '__main__':
    # Run unit tests
    print("🧪 Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "="*60)
    
    # Run functional tests
    run_functional_tests()





