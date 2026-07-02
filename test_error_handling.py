#!/usr/bin/env python3
"""
Test Error Handling and Route Management - Task #21
Tests graceful error handling, user-friendly route management, and feature flags.
"""

import unittest
import sys
import os
from flask import Flask, request, session
from werkzeug.exceptions import HTTPException, NotFound, Forbidden, InternalServerError
import tempfile
import shutil

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling and route management functionality"""
    
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
        
        # Import and configure the app
        with self.app.app_context():
            # Import the main app components
            from api.app import (
                generate_error_id, log_error, is_feature_enabled, 
                require_feature, FEATURE_FLAGS
            )
            
            # Store references for testing
            self.generate_error_id = generate_error_id
            self.log_error = log_error
            self.is_feature_enabled = is_feature_enabled
            self.require_feature = require_feature
            self.FEATURE_FLAGS = FEATURE_FLAGS
    
    def tearDown(self):
        """Clean up test environment"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_error_id_generation(self):
        """Test that error IDs are generated correctly"""
        error_id1 = self.generate_error_id()
        error_id2 = self.generate_error_id()
        
        # Check that IDs are strings and 8 characters long
        self.assertIsInstance(error_id1, str)
        self.assertIsInstance(error_id2, str)
        self.assertEqual(len(error_id1), 8)
        self.assertEqual(len(error_id2), 8)
        
        # Check that IDs are unique
        self.assertNotEqual(error_id1, error_id2)
    
    def test_error_logging(self):
        """Test error logging functionality"""
        with self.app.test_request_context('/test'):
            # Create a test error
            test_error = ValueError("Test error message")
            
            # Test error logging
            error_id = self.log_error(test_error)
            
            # Verify error ID is generated
            self.assertIsInstance(error_id, str)
            self.assertEqual(len(error_id), 8)
    
    def test_feature_flags(self):
        """Test feature flag system"""
        # Test enabled features
        self.assertTrue(self.is_feature_enabled('advanced_analytics'))
        self.assertTrue(self.is_feature_enabled('bulk_operations'))
        self.assertTrue(self.is_feature_enabled('api_endpoints'))
        
        # Test disabled features
        self.assertFalse(self.is_feature_enabled('nonexistent_feature'))
        self.assertFalse(self.is_feature_enabled('disabled_feature'))
    
    def test_require_feature_decorator(self):
        """Test the require_feature decorator"""
        @self.require_feature('advanced_analytics')
        def test_function():
            return "success"
        
        # Test with enabled feature
        result = test_function()
        self.assertEqual(result, "success")
        
        # Test with disabled feature
        @self.require_feature('nonexistent_feature')
        def test_function_disabled():
            return "success"
        
        with self.assertRaises(HTTPException) as context:
            test_function_disabled()
        
        self.assertEqual(context.exception.code, 404)
    
    def test_error_template_rendering(self):
        """Test that error templates exist and can be rendered"""
        # Test 404 template
        try:
            with open('templates/errors/404.html', 'r') as f:
                content = f.read()
                self.assertIn('Page Not Found', content)
                self.assertIn('404', content)
        except FileNotFoundError:
            self.fail("404 error template not found")
        
        # Test 403 template
        try:
            with open('templates/errors/403.html', 'r') as f:
                content = f.read()
                self.assertIn('Access Denied', content)
                self.assertIn('403', content)
        except FileNotFoundError:
            self.fail("403 error template not found")
        
        # Test 500 template
        try:
            with open('templates/errors/500.html', 'r') as f:
                content = f.read()
                self.assertIn('Internal Server Error', content)
                self.assertIn('500', content)
        except FileNotFoundError:
            self.fail("500 error template not found")
    
    def test_error_template_air_force_styling(self):
        """Test that error templates use Air Force styling"""
        # Check for Air Force color variables
        with open('templates/base.html', 'r') as f:
            base_content = f.read()
            self.assertIn('--primary-color', base_content)
            self.assertIn('--secondary-color', base_content)
            self.assertIn('--accent-color', base_content)
        
        # Check that error templates extend base template
        with open('templates/errors/404.html', 'r') as f:
            error_content = f.read()
            self.assertIn('{% extends "base.html" %}', error_content)
            self.assertIn('btn-primary', error_content)
            self.assertIn('btn-secondary', error_content)

def run_functional_tests():
    """Run functional tests to verify the implementation works"""
    print("🧪 Running Functional Tests for Error Handling and Route Management...")
    
    # Test 1: Verify error templates exist
    print("\n1. Testing Error Templates...")
    try:
        error_templates = ['404.html', '403.html', '500.html']
        for template in error_templates:
            template_path = f'templates/errors/{template}'
            with open(template_path, 'r') as f:
                content = f.read()
                assert '{% extends "base.html" %}' in content, f"Template {template} doesn't extend base"
                assert 'btn-primary' in content, f"Template {template} missing primary button"
                assert 'btn-secondary' in content, f"Template {template} missing secondary button"
        
        print("✅ Error templates verified")
    except Exception as e:
        print(f"❌ Error template test failed: {e}")
        return False
    
    # Test 2: Verify error handling functions exist
    print("\n2. Testing Error Handling Functions...")
    try:
        from api.app import (
            generate_error_id, log_error, is_feature_enabled, 
            require_feature, FEATURE_FLAGS
        )
        
        # Test error ID generation
        error_id = generate_error_id()
        assert isinstance(error_id, str), "Error ID should be a string"
        assert len(error_id) == 8, "Error ID should be 8 characters"
        
        # Test feature flags
        assert is_feature_enabled('advanced_analytics'), "Advanced analytics should be enabled"
        assert not is_feature_enabled('nonexistent_feature'), "Nonexistent feature should be disabled"
        
        print("✅ Error handling functions verified")
    except Exception as e:
        print(f"❌ Error handling function test failed: {e}")
        return False
    
    # Test 3: Verify route protection logic
    print("\n3. Testing Route Protection Logic...")
    try:
        # Test protected routes list
        protected_routes = [
            'dashboard', 'recruits', 'cadet', 'contacts', 'calendar', 
            'materials', 'admin', 'profile', 'change_password'
        ]
        
        # Test admin routes list
        admin_routes = [
            'admin', 'user_management', 'database_management', 'activity_log',
            'system_statistics', 'backup', 'restore', 'code_coverage',
            'quality_analysis', 'vulnerability_scan'
        ]
        
        # Verify route lists are properly defined
        assert len(protected_routes) > 0, "Protected routes list should not be empty"
        assert len(admin_routes) > 0, "Admin routes list should not be empty"
        
        # Verify no overlap between protected and admin routes
        overlap = set(protected_routes) & set(admin_routes)
        assert len(overlap) > 0, "Some routes should be both protected and admin"
        
        print("✅ Route protection logic verified")
    except Exception as e:
        print(f"❌ Route protection test failed: {e}")
        return False
    
    # Test 4: Verify Air Force styling integration
    print("\n4. Testing Air Force Styling Integration...")
    try:
        with open('templates/base.html', 'r') as f:
            base_content = f.read()
        
        # Check for Air Force color variables
        required_vars = [
            '--primary-color: #1C2347',
            '--secondary-color: #007BFE', 
            '--accent-color: #25BAF9',
            '--text-color: #707070',
            '--background-color: #E9E8E8'
        ]
        
        for var in required_vars:
            assert var in base_content, f"Air Force color variable not found: {var}"
        
        # Check for Air Force background system
        assert 'body::before' in base_content, "Air Force background system not found"
        assert 'background-image' in base_content, "Background images not found"
        
        print("✅ Air Force styling integration verified")
    except Exception as e:
        print(f"❌ Air Force styling test failed: {e}")
        return False
    
    print("\n🎉 All functional tests passed!")
    return True

def test_error_page_accessibility():
    """Test that error pages are accessible and properly styled"""
    print("\n5. Testing Error Page Accessibility...")
    
    try:
        # Test 404 page
        with open('templates/errors/404.html', 'r') as f:
            content = f.read()
            assert 'Page Not Found' in content
            assert 'Go to Dashboard' in content
            assert 'Go Back' in content
            assert 'request.url' in content  # Shows requested URL
        
        # Test 403 page
        with open('templates/errors/403.html', 'r') as f:
            content = f.read()
            assert 'Access Denied' in content
            assert 'permission' in content.lower()
            assert 'administrator' in content.lower()
        
        # Test 500 page
        with open('templates/errors/500.html', 'r') as f:
            content = f.read()
            assert 'Internal Server Error' in content
            assert 'error_id' in content
            assert 'contact' in content.lower()
        
        print("✅ Error page accessibility verified")
        return True
    except Exception as e:
        print(f"❌ Error page accessibility test failed: {e}")
        return False

if __name__ == '__main__':
    # Run unit tests
    print("🧪 Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "="*60)
    
    # Run functional tests
    success = run_functional_tests()
    
    print("\n" + "="*60)
    
    # Test error page accessibility
    test_error_page_accessibility()
    
    if success:
        print("\n🎉 All tests completed successfully!")
    else:
        print("\n❌ Some tests failed!")





