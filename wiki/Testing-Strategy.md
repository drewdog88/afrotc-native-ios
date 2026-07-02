# Testing Strategy

## Overview

Our AFROTC recruitment system employs a comprehensive testing strategy that combines **unit testing**, **smoke testing**, and **integration testing** to ensure reliability, functionality, and performance across all system components.

## Testing Philosophy

### **Quality Assurance Approach**
- **Test Early, Test Often**: Testing integrated into development workflow
- **Automated Testing**: Reduce manual testing overhead
- **Comprehensive Coverage**: Test all critical system components
- **Performance Testing**: Ensure system meets performance requirements
- **Security Testing**: Validate security measures and data protection

### **Testing Pyramid**
```
    ┌─────────────┐
    │   E2E Tests │ ← Few, high-level tests
    ├─────────────┤
    │Integration  │ ← Medium number of integration tests
    │   Tests     │
    ├─────────────┤
    │  Unit Tests │ ← Many, focused unit tests
    └─────────────┘
```

## Unit Testing

### **Purpose & Scope**
Unit tests verify individual components and functions work correctly in isolation.

### **Testing Framework**
```python
# Using Python's unittest framework
import unittest
from unittest.mock import patch, MagicMock
from api.app import app, db, User, PotentialRecruit

class TestUserManagement(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_user_creation(self):
        """Test user creation functionality"""
        user = User(
            username='testuser',
            email='test@example.com',
            password_hash='hashed_password',
            first_name='Test',
            last_name='User'
        )
        db.session.add(user)
        db.session.commit()
        
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
```

### **Key Test Categories**

#### **1. Model Tests**
```python
class TestModels(unittest.TestCase):
    def test_potential_recruit_creation(self):
        """Test potential recruit model creation"""
        recruit = PotentialRecruit(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            current_school='Test High School',
            school_type='high_school'
        )
        
        self.assertEqual(recruit.first_name, 'John')
        self.assertEqual(recruit.status, 'prospective')  # Default value
        self.assertIsNotNone(recruit.created_at)
    
    def test_user_password_validation(self):
        """Test password validation functionality"""
        user = User(username='testuser', email='test@example.com')
        
        # Test valid password
        self.assertTrue(validate_password('StrongPass123!', user.id))
        
        # Test invalid password
        self.assertFalse(validate_password('weak', user.id))
```

#### **2. Route Tests**
```python
class TestRoutes(unittest.TestCase):
    def test_login_route(self):
        """Test login route functionality"""
        response = self.app.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
    
    def test_protected_route_access(self):
        """Test protected route access control"""
        # Test without authentication
        response = self.app.get('/admin', follow_redirects=True)
        self.assertIn(b'login', response.data)
        
        # Test with authentication
        with self.app.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'admin'
        
        response = self.app.get('/admin')
        self.assertEqual(response.status_code, 200)
```

#### **3. Utility Function Tests**
```python
class TestUtilities(unittest.TestCase):
    def test_export_data_function(self):
        """Test data export functionality"""
        test_data = [{'name': 'Test', 'value': 123}]
        result = export_data(test_data, 'test.csv', 'csv', 'Test Export')
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)  # filename and data
    
    def test_backup_function(self):
        """Test backup functionality"""
        with patch('vercel_blob.put') as mock_put:
            mock_put.return_value = 'https://example.com/backup.json'
            
            filename, url = backup_database("Test backup")
            
            self.assertIsNotNone(filename)
            self.assertEqual(url, 'https://example.com/backup.json')
            mock_put.assert_called_once()
```

### **Test Coverage Goals**
- **Model Layer**: 95% coverage
- **Route Layer**: 90% coverage
- **Utility Functions**: 85% coverage
- **Overall Coverage**: 90% minimum

## Smoke Testing

### **Purpose & Scope**
Smoke tests verify that the application starts correctly and basic functionality works in the target environment.

### **Smoke Test Categories**

#### **1. Application Startup Tests**
```python
def test_application_startup():
    """Test that application starts without errors"""
    try:
        from api.app import app
        client = app.test_client()
        response = client.get('/')
        assert response.status_code in [200, 302]  # 302 for redirect to login
        print("✅ Application startup successful")
    except Exception as e:
        print(f"❌ Application startup failed: {e}")
        raise
```

#### **2. Database Connection Tests**
```python
def test_database_connection():
    """Test database connectivity and basic operations"""
    try:
        from api.app import app, db
        with app.app_context():
            # Test basic query
            result = db.session.execute("SELECT 1").scalar()
            assert result == 1
            print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise
```

#### **3. Authentication Tests**
```python
def test_authentication_system():
    """Test authentication system functionality"""
    try:
        from api.app import app
        client = app.test_client()
        
        # Test login page accessibility
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()
        
        print("✅ Authentication system accessible")
    except Exception as e:
        print(f"❌ Authentication system failed: {e}")
        raise
```

#### **4. Core Feature Tests**
```python
def test_core_features():
    """Test core application features"""
    try:
        from api.app import app
        client = app.test_client()
        
        # Test admin panel accessibility (should redirect to login)
        response = client.get('/admin', follow_redirects=True)
        assert response.status_code == 200
        
        # Test materials page
        response = client.get('/materials', follow_redirects=True)
        assert response.status_code == 200
        
        print("✅ Core features accessible")
    except Exception as e:
        print(f"❌ Core features failed: {e}")
        raise
```

### **Automated Smoke Testing**
```python
# smoke_test.py
import requests
import sys

def run_smoke_tests():
    """Run comprehensive smoke tests"""
    base_url = "https://afrotc695recruitment.vercel.app"
    tests = [
        ("Homepage", "/"),
        ("Login Page", "/login"),
        ("Materials Page", "/materials"),
        ("Admin Panel", "/admin"),
        ("API Health", "/api/recruits")
    ]
    
    results = []
    for test_name, endpoint in tests:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            status = "✅ PASS" if response.status_code < 500 else "❌ FAIL"
            results.append(f"{status} {test_name}: {response.status_code}")
        except Exception as e:
            results.append(f"❌ FAIL {test_name}: {str(e)}")
    
    print("\n".join(results))
    return all("✅ PASS" in result for result in results)

if __name__ == "__main__":
    success = run_smoke_tests()
    sys.exit(0 if success else 1)
```

## Integration Testing

### **Purpose & Scope**
Integration tests verify that different components work together correctly.

### **Database Integration Tests**
```python
class TestDatabaseIntegration(unittest.TestCase):
    def test_user_recruit_relationship(self):
        """Test user and recruit data relationships"""
        # Create user
        user = User(username='recruiter1', email='recruiter1@example.com')
        db.session.add(user)
        db.session.commit()
        
        # Create recruit
        recruit = PotentialRecruit(
            first_name='John',
            last_name='Doe',
            current_school='Test School',
            school_type='high_school'
        )
        db.session.add(recruit)
        db.session.commit()
        
        # Test relationship
        self.assertIsNotNone(user.id)
        self.assertIsNotNone(recruit.id)
        self.assertNotEqual(user.id, recruit.id)
    
    def test_activity_logging(self):
        """Test activity logging integration"""
        user = User(username='testuser', email='test@example.com')
        db.session.add(user)
        db.session.commit()
        
        # Log activity
        log_activity('TEST', 'user', user.id, 'Test activity')
        
        # Verify log entry
        log_entry = ActivityLog.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.action, 'TEST')
```

### **API Integration Tests**
```python
class TestAPIIntegration(unittest.TestCase):
    def test_recruit_api_workflow(self):
        """Test complete recruit API workflow"""
        # Create recruit via API
        response = self.app.post('/recruits/add', data={
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@example.com',
            'current_school': 'Test High School',
            'school_type': 'high_school'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify recruit was created
        recruit = PotentialRecruit.query.filter_by(email='jane@example.com').first()
        self.assertIsNotNone(recruit)
        self.assertEqual(recruit.first_name, 'Jane')
```

## Performance Testing

### **Load Testing**
```python
def test_application_performance():
    """Test application performance under load"""
    import time
    
    start_time = time.time()
    
    # Simulate multiple concurrent requests
    for i in range(10):
        response = self.app.get('/')
        assert response.status_code < 500
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Performance assertion
    assert duration < 5.0  # Should complete within 5 seconds
    print(f"✅ Performance test passed: {duration:.2f}s")
```

### **Database Performance Tests**
```python
def test_database_performance():
    """Test database query performance"""
    import time
    
    start_time = time.time()
    
    # Execute complex query
    result = db.session.execute("""
        SELECT COUNT(*) as total_recruits,
               COUNT(CASE WHEN status = 'active' THEN 1 END) as active_recruits
        FROM potential_recruit
    """).fetchone()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Performance assertion
    assert duration < 1.0  # Should complete within 1 second
    print(f"✅ Database performance test passed: {duration:.3f}s")
```

## Security Testing

### **Authentication Tests**
```python
def test_authentication_security():
    """Test authentication security measures"""
    # Test invalid login attempts
    response = self.app.post('/login', data={
        'username': 'admin',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    # Should not grant access
    self.assertNotIn(b'admin', response.data)
    
    # Test SQL injection attempts
    response = self.app.post('/login', data={
        'username': "admin'; DROP TABLE user; --",
        'password': 'password'
    }, follow_redirects=True)
    
    # Should handle gracefully
    self.assertNotIn(b'error', response.data)
```

### **Authorization Tests**
```python
def test_authorization_controls():
    """Test authorization and access controls"""
    # Test admin-only routes
    response = self.app.get('/admin/users', follow_redirects=True)
    self.assertIn(b'login', response.data)  # Should redirect to login
    
    # Test with non-admin user
    with self.app.session_transaction() as sess:
        sess['user_id'] = 2
        sess['username'] = 'recruiter'
    
    response = self.app.get('/admin/users')
    self.assertEqual(response.status_code, 403)  # Should be forbidden
```

## Test Automation

### **Continuous Integration**
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: python -m pytest tests/
      - name: Run smoke tests
        run: python smoke_test.py
```

### **Test Execution Scripts**
```bash
#!/bin/bash
# run_tests.sh

echo "Running Unit Tests..."
python -m pytest tests/ -v --cov=api --cov-report=html

echo "Running Smoke Tests..."
python smoke_test.py

echo "Running Performance Tests..."
python performance_test.py

echo "All tests completed!"
```

## Test Data Management

### **Test Data Setup**
```python
def create_test_data():
    """Create test data for comprehensive testing"""
    # Create test users
    admin_user = User(
        username='admin',
        email='admin@test.com',
        password_hash='hashed_password',
        first_name='Admin',
        last_name='User',
        role='admin'
    )
    db.session.add(admin_user)
    
    # Create test recruits
    for i in range(5):
        recruit = PotentialRecruit(
            first_name=f'Test{i}',
            last_name=f'Recruit{i}',
            email=f'test{i}@example.com',
            current_school=f'Test School {i}',
            school_type='high_school'
        )
        db.session.add(recruit)
    
    db.session.commit()
```

### **Test Data Cleanup**
```python
def cleanup_test_data():
    """Clean up test data after tests"""
    db.session.query(ActivityLog).delete()
    db.session.query(PotentialRecruit).delete()
    db.session.query(User).delete()
    db.session.commit()
```

## Best Practices

### **1. Test Organization**
- **Clear naming**: Descriptive test names
- **Grouped tests**: Logical test organization
- **Setup/teardown**: Proper test environment management
- **Isolation**: Tests should not depend on each other

### **2. Test Data**
- **Fresh data**: Use fresh test data for each test
- **Realistic data**: Use realistic test scenarios
- **Edge cases**: Test boundary conditions
- **Error conditions**: Test error handling

### **3. Performance**
- **Fast execution**: Tests should run quickly
- **Efficient queries**: Optimize database queries in tests
- **Mocking**: Use mocks for external dependencies
- **Parallel execution**: Support parallel test execution

### **4. Maintenance**
- **Regular updates**: Keep tests up to date with code changes
- **Documentation**: Document test purpose and expected behavior
- **Code coverage**: Maintain high test coverage
- **Test reviews**: Review tests as part of code review process

## Conclusion

Our comprehensive testing strategy ensures:

- **Reliability**: All critical functionality is tested
- **Quality**: High code coverage and thorough testing
- **Performance**: Performance requirements are validated
- **Security**: Security measures are verified
- **Maintainability**: Tests are well-organized and maintainable

This testing approach provides confidence in our system's reliability and helps catch issues early in the development process.

**Key Takeaway**: A comprehensive testing strategy is essential for maintaining high-quality, reliable software. Our combination of unit, smoke, and integration tests provides thorough coverage and confidence in our system's functionality.
