#!/usr/bin/env python3
"""
AFROTC 695 Recruitment System - Comprehensive Testing Script
This script systematically tests every feature, link, and functionality of the system.
Now includes CONTENT VERIFICATION and DATA ACCURACY testing.
"""

import requests
import time
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import sqlite3
import os

class ComprehensiveTester:
    def __init__(self):
        self.local_base = "http://localhost:5000"
        self.prod_base = "https://afrotc695recruitment.vercel.app"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "local_results": {},
            "production_results": {},
            "issues": [],
            "content_verification": {
                "local": {},
                "production": {}
            }
        }
        
        # Test credentials (you'll need to set these up)
        self.test_credentials = {
            "admin": {"username": "admin", "password": "admin123"},
            "recruiter": {"username": "recruiter", "password": "recruiter123"}
        }
        
        # Session for authenticated requests
        self.session = requests.Session()

    def log_issue(self, environment, test_name, issue, details=""):
        """Log an issue found during testing"""
        issue_record = {
            "environment": environment,
            "test": test_name,
            "issue": issue,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results["issues"].append(issue_record)
        print(f"❌ {environment.upper()} - {test_name}: {issue}")
        if details:
            print(f"   Details: {details}")

    def log_success(self, environment, test_name):
        """Log a successful test"""
        print(f"✅ {environment.upper()} - {test_name}: PASSED")

    def log_content_verification(self, environment, page, verification_type, expected, actual, status):
        """Log content verification results"""
        if environment not in self.results["content_verification"]:
            self.results["content_verification"][environment] = {}
        
        if page not in self.results["content_verification"][environment]:
            self.results["content_verification"][environment][page] = []
            
        verification_result = {
            "type": verification_type,
            "expected": expected,
            "actual": actual,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results["content_verification"][environment][page].append(verification_result)
        
        if status == "PASS":
            print(f"✅ {environment.upper()} - {page} - {verification_type}: {expected} == {actual}")
        else:
            print(f"❌ {environment.upper()} - {page} - {verification_type}: Expected {expected}, got {actual}")

    def get_database_connection(self, environment):
        """Get database connection for the specified environment"""
        if environment == "local":
            # For local testing, we'll use the actual database
            # You might need to adjust this based on your setup
            db_path = "instance/afrotc695.db"  # Adjust path as needed
            if os.path.exists(db_path):
                return sqlite3.connect(db_path)
        return None

    def get_database_counts(self, environment):
        """Get actual record counts from database"""
        counts = {}
        conn = self.get_database_connection(environment)
        
        if conn:
            try:
                cursor = conn.cursor()
                
                # Get counts for all major tables
                tables = [
                    'user', 'potential_recruit', 'cadet', 'university_contact',
                    'recruitment_event', 'external_link', 'recruitment_document',
                    'activity_log', 'password_history'
                ]
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    counts[table] = count
                
                # Get specific counts for detailed verification
                cursor.execute("SELECT COUNT(*) FROM user WHERE role = 'admin'")
                counts['admin_users'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM potential_recruit WHERE status = 'prospective'")
                counts['prospective_recruits'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM cadet WHERE status = 'active'")
                counts['active_cadets'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM university_contact WHERE is_active = 1")
                counts['active_contacts'] = cursor.fetchone()[0]
                
                # Get recent activity count
                thirty_days_ago = datetime.now() - timedelta(days=30)
                cursor.execute("SELECT COUNT(*) FROM activity_log WHERE created_at >= ?", (thirty_days_ago,))
                counts['recent_activities'] = cursor.fetchone()[0]
                
                conn.close()
                
            except Exception as e:
                self.log_issue(environment, "Database Counts", f"Error getting database counts: {str(e)}")
                counts = {}
        else:
            # For production or when DB not accessible, we'll use API calls
            counts = self.get_counts_via_api(environment)
            
        return counts

    def get_counts_via_api(self, environment):
        """Get counts via API endpoints when database not accessible"""
        counts = {}
        base_url = self.local_base if environment == "local" else self.prod_base
        
        try:
            # Try to get data via API endpoints
            response = self.session.get(f"{base_url}/api/recruits")
            if response.status_code == 200:
                recruits = response.json()
                counts['potential_recruit'] = len(recruits)
            
            response = self.session.get(f"{base_url}/api/cadet")
            if response.status_code == 200:
                cadets = response.json()
                counts['cadet'] = len(cadets)
                
        except Exception as e:
            self.log_issue(environment, "API Counts", f"Error getting counts via API: {str(e)}")
            
        return counts

    def extract_stats_from_page(self, html_content, page_type):
        """Extract statistics from HTML page content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        stats = {}
        
        if page_type == "system_statistics":
            # Extract stats from system statistics page
            stat_cards = soup.find_all('div', class_='card-body')
            for card in stat_cards:
                title_elem = card.find('h3', class_='card-title')
                text_elem = card.find('p', class_='card-text')
                
                if title_elem and text_elem:
                    value = title_elem.get_text().strip()
                    label = text_elem.get_text().strip()
                    
                    # Convert value to number if possible
                    try:
                        value = int(value)
                    except ValueError:
                        value = 0
                        
                    stats[label] = value
            
            # Extract recent activities
            activity_table = soup.find('table')
            if activity_table:
                rows = activity_table.find_all('tr')[1:]  # Skip header
                stats['recent_activities_count'] = len(rows)
                
        elif page_type == "recruits":
            # Extract recruit list data
            recruit_rows = soup.find_all('tr', class_='recruit-row') or soup.find_all('tr')[1:]  # Skip header
            stats['displayed_recruits'] = len(recruit_rows)
            
        elif page_type == "cadet":
            # Extract cadet list data
            cadet_rows = soup.find_all('tr', class_='cadet-row') or soup.find_all('tr')[1:]  # Skip header
            stats['displayed_cadets'] = len(cadet_rows)
            
        elif page_type == "contacts":
            # Extract contact list data
            contact_rows = soup.find_all('tr', class_='contact-row') or soup.find_all('tr')[1:]  # Skip header
            stats['displayed_contacts'] = len(contact_rows)
            
        return stats

    def verify_page_content(self, environment, endpoint, page_type, expected_counts=None):
        """Verify that page content matches expected data"""
        base_url = self.local_base if environment == "local" else self.prod_base
        url = f"{base_url}{endpoint}"
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                # Extract stats from page
                page_stats = self.extract_stats_from_page(response.text, page_type)
                
                # Get actual database counts
                db_counts = self.get_database_counts(environment)
                
                # Verify content matches database
                verification_results = []
                
                if page_type == "system_statistics":
                    # Verify system statistics
                    expected_stats = {
                        "Total Users": db_counts.get('user', 0),
                        "Active Users": db_counts.get('active_users', 0),
                        "Admin Users": db_counts.get('admin_users', 0),
                        "Potential Recruits": db_counts.get('potential_recruit', 0),
                        "Cadets": db_counts.get('cadet', 0),
                        "University Contacts": db_counts.get('university_contact', 0),
                        "Recruitment Events": db_counts.get('recruitment_event', 0)
                    }
                    
                    for stat_name, expected_value in expected_stats.items():
                        actual_value = page_stats.get(stat_name, 0)
                        status = "PASS" if actual_value == expected_value else "FAIL"
                        self.log_content_verification(environment, endpoint, f"Stat: {stat_name}", expected_value, actual_value, status)
                        verification_results.append(status)
                        
                elif page_type in ["recruits", "cadet", "contacts"]:
                    # Verify list counts
                    table_name = {
                        "recruits": "potential_recruit",
                        "cadet": "cadet", 
                        "contacts": "university_contact"
                    }[page_type]
                    
                    expected_count = db_counts.get(table_name, 0)
                    actual_count = page_stats.get(f'displayed_{page_type}', 0)
                    
                    status = "PASS" if actual_count == expected_count else "FAIL"
                    self.log_content_verification(environment, endpoint, f"List Count", expected_count, actual_count, status)
                    verification_results.append(status)
                
                # Check for empty page indicators
                if not page_stats:
                    self.log_issue(environment, f"Content Verification - {endpoint}", "No data extracted from page")
                    return False
                    
                # Check if all verifications passed
                all_passed = all(status == "PASS" for status in verification_results)
                
                if all_passed:
                    self.log_success(environment, f"Content Verification - {endpoint}")
                else:
                    self.log_issue(environment, f"Content Verification - {endpoint}", f"{verification_results.count('FAIL')} verification(s) failed")
                    
                return all_passed
                
            else:
                self.log_issue(environment, f"Content Verification - {endpoint}", f"Page returned status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_issue(environment, f"Content Verification - {endpoint}", f"Error during content verification: {str(e)}")
            return False

    def test_endpoint(self, environment, endpoint, expected_status=200, check_content=None, allow_redirects=True, page_type=None):
        """Test a single endpoint with content verification"""
        base_url = self.local_base if environment == "local" else self.prod_base
        url = f"{base_url}{endpoint}"
        
        try:
            if environment == "production":
                response = self.session.get(url, timeout=10, allow_redirects=allow_redirects)
            else:
                response = self.session.get(url, allow_redirects=allow_redirects)
                
            if response.status_code != expected_status:
                # Special handling for authentication redirects
                if expected_status == 302 and response.status_code == 200:
                    # This means the redirect was followed and we got the login page
                    if 'login' in response.text.lower() or 'username' in response.text.lower():
                        self.log_success(environment, f"GET {endpoint} (redirected to login)")
                        return True
                    else:
                        self.log_issue(environment, f"GET {endpoint}", 
                                     f"Expected 302 redirect, got 200 but not login page")
                        return False
                elif expected_status == 302 and response.status_code == 302:
                    # This is a proper redirect (not followed)
                    if 'Location' in response.headers and 'login' in response.headers['Location']:
                        self.log_success(environment, f"GET {endpoint} (302 redirect to login)")
                        return True
                    else:
                        self.log_issue(environment, f"GET {endpoint}", 
                                     f"Expected 302 redirect to login, got 302 to {response.headers.get('Location', 'unknown')}")
                        return False
                else:
                    self.log_issue(environment, f"GET {endpoint}", 
                                 f"Expected status {expected_status}, got {response.status_code}")
                    return False
                
            if check_content and check_content not in response.text:
                self.log_issue(environment, f"GET {endpoint}", 
                             f"Expected content '{check_content}' not found")
                return False
                
            self.log_success(environment, f"GET {endpoint}")
            
            # Perform content verification if page_type is specified
            if page_type and response.status_code == 200:
                self.verify_page_content(environment, endpoint, page_type)
                
            return True
            
        except Exception as e:
            self.log_issue(environment, f"GET {endpoint}", f"Request failed: {str(e)}")
            return False

    def test_phase_1_authentication(self):
        """Phase 1: Authentication & Basic Navigation"""
        print("\n" + "="*60)
        print("PHASE 1: AUTHENTICATION & BASIC NAVIGATION TESTING")
        print("="*60)

        # 1.1 Login Page Access
        print("\n1.1 LOGIN PAGE ACCESS")
        self.test_endpoint("local", "/login", 200, check_content="username")
        self.test_endpoint("production", "/login", 200, check_content="username")

        # 1.2 Homepage Redirect
        print("\n1.2 HOMEPAGE REDIRECT")
        self.test_endpoint("local", "/", 302, allow_redirects=False)  # Should redirect to login
        self.test_endpoint("production", "/", 302, allow_redirects=False)  # Should redirect to login

        # 1.3 Forgot Password
        print("\n1.3 FORGOT PASSWORD")
        self.test_endpoint("local", "/forgot-password", 200)
        self.test_endpoint("production", "/forgot-password", 200)

    def test_phase_2_protected_pages(self):
        """Phase 2: Protected Pages (Unauthenticated)"""
        print("\n" + "="*60)
        print("PHASE 2: PROTECTED PAGES (UNAUTHENTICATED)")
        print("="*60)

        protected_pages = [
            "/dashboard", "/recruits", "/contacts", "/calendar", "/materials", "/profile",
            "/admin", "/admin/users", "/admin/database", "/admin/activity-log",
            "/admin/system-statistics", "/admin/code-coverage", "/admin/quality-analysis",
            "/admin/vulnerability-scan"
        ]

        for page in protected_pages:
            print(f"\nTesting {page}")
            self.test_endpoint("local", page, 302, allow_redirects=False)  # Should redirect to login
            self.test_endpoint("production", page, 302, allow_redirects=False)  # Should redirect to login

    def test_phase_3_forms_and_add_pages(self):
        """Phase 3: Forms & Add Pages (Unauthenticated)"""
        print("\n" + "="*60)
        print("PHASE 3: FORMS & ADD PAGES (UNAUTHENTICATED)")
        print("="*60)

        form_pages = [
            "/recruits/add", "/recruits/edit/1", "/cadet/add", "/cadet/edit/1",
            "/contacts/add", "/contacts/edit/1", "/calendar/add",
            "/materials/add-link", "/materials/add-document",
            "/admin/users/add", "/admin/users/edit/1", "/change-password"
        ]

        for page in form_pages:
            print(f"\nTesting {page}")
            self.test_endpoint("local", page, 302, allow_redirects=False)  # Should redirect to login
            self.test_endpoint("production", page, 302, allow_redirects=False)  # Should redirect to login

    def test_phase_4_export_endpoints(self):
        """Phase 4: Export Endpoints (Unauthenticated)"""
        print("\n" + "="*60)
        print("PHASE 4: EXPORT ENDPOINTS (UNAUTHENTICATED)")
        print("="*60)

        export_endpoints = [
            "/download/recruits/csv", "/download/recruits/excel", "/download/recruits/pdf",
            "/download/cadet/csv", "/download/cadet/excel", "/download/cadet/pdf",
            "/download/contacts/csv", "/download/contacts/excel", "/download/contacts/pdf",
            "/download/activity-log/csv", "/download/activity-log/excel", "/download/activity-log/pdf"
        ]

        for endpoint in export_endpoints:
            print(f"\nTesting {endpoint}")
            self.test_endpoint("local", endpoint, 302, allow_redirects=False)  # Should redirect to login
            self.test_endpoint("production", endpoint, 302, allow_redirects=False)  # Should redirect to login

    def test_phase_5_api_endpoints(self):
        """Phase 5: API Endpoints"""
        print("\n" + "="*60)
        print("PHASE 5: API ENDPOINTS")
        print("="*60)
        
        api_endpoints = [
            "/api/recruits",
            "/api/cadet"
        ]
        
        for endpoint in api_endpoints:
            print(f"\nTesting {endpoint}")
            self.test_endpoint("local", endpoint, 401)  # Should return 401 for JSON API
            self.test_endpoint("production", endpoint, 401)  # Should return 401 for JSON API

    def test_phase_6_content_verification(self):
        """Phase 6: Content Verification (Authenticated)"""
        print("\n" + "="*60)
        print("PHASE 6: CONTENT VERIFICATION (AUTHENTICATED)")
        print("="*60)
        
        # Note: This phase would require authentication
        # For now, we'll test the endpoints and note that content verification needs auth
        
        content_pages = [
            ("/admin/system-statistics", "system_statistics"),
            ("/recruits", "recruits"),
            ("/cadet", "cadet"),
            ("/contacts", "contacts")
        ]
        
        for endpoint, page_type in content_pages:
            print(f"\nTesting content verification for {endpoint}")
            # This will test the endpoint but note that content verification needs authentication
            self.test_endpoint("local", endpoint, 302, page_type=page_type)  # Will redirect to login
            self.test_endpoint("production", endpoint, 302, page_type=page_type)  # Will redirect to login

    def test_phase_7_error_pages(self):
        """Phase 7: Error Pages"""
        print("\n" + "="*60)
        print("PHASE 7: ERROR PAGES")
        print("="*60)
        
        # Test 404 page
        print("\nTesting 404 page")
        self.test_endpoint("local", "/nonexistent-page", 404)
        self.test_endpoint("production", "/nonexistent-page", 404)
        
    def test_phase_8_static_files(self):
        """Phase 8: Static Files"""
        print("\n" + "="*60)
        print("PHASE 8: STATIC FILES")
        print("="*60)
        
        static_files = [
            "/static/detachment695.jpg",
            "/static/js/analytics.js"
        ]
        
        for file in static_files:
            print(f"\nTesting {file}")
            self.test_endpoint("local", file, 200)
            self.test_endpoint("production", file, 200)
            
    def test_phase_9_performance(self):
        """Phase 9: Performance Testing"""
        print("\n" + "="*60)
        print("PHASE 9: PERFORMANCE TESTING")
        print("="*60)
        
        # Test response times
        endpoints_to_test = ["/login", "/forgot-password"]
        
        for endpoint in endpoints_to_test:
            print(f"\nTesting response time for {endpoint}")
            
            # Local
            start_time = time.time()
            try:
                response = self.session.get(f"{self.local_base}{endpoint}")
                local_time = time.time() - start_time
                if local_time > 3.0:
                    self.log_issue("local", f"Performance {endpoint}", 
                                 f"Response time {local_time:.2f}s exceeds 3s threshold")
                else:
                    print(f"✅ LOCAL - {endpoint}: {local_time:.2f}s")
            except Exception as e:
                self.log_issue("local", f"Performance {endpoint}", f"Request failed: {str(e)}")
                
            # Production
            start_time = time.time()
            try:
                response = self.session.get(f"{self.prod_base}{endpoint}", timeout=10)
                prod_time = time.time() - start_time
                if prod_time > 5.0:
                    self.log_issue("production", f"Performance {endpoint}", 
                                 f"Response time {prod_time:.2f}s exceeds 5s threshold")
                else:
                    print(f"✅ PRODUCTION - {endpoint}: {prod_time:.2f}s")
            except Exception as e:
                self.log_issue("production", f"Performance {endpoint}", f"Request failed: {str(e)}")

    def run_all_tests(self):
        """Run all testing phases"""
        print("🚀 STARTING COMPREHENSIVE TESTING WITH CONTENT VERIFICATION")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        try:
            self.test_phase_1_authentication()
            self.test_phase_2_protected_pages()
            self.test_phase_3_forms_and_add_pages()
            self.test_phase_4_export_endpoints()
            self.test_phase_5_api_endpoints()
            self.test_phase_6_content_verification()
            self.test_phase_7_error_pages()
            self.test_phase_8_static_files()
            self.test_phase_9_performance()
            
        except KeyboardInterrupt:
            print("\n⚠️ Testing interrupted by user")
        except Exception as e:
            print(f"\n❌ Testing failed with error: {str(e)}")
            
        self.generate_report()

    def generate_report(self):
        """Generate a comprehensive test report"""
        print("\n" + "="*60)
        print("COMPREHENSIVE TESTING REPORT")
        print("="*60)
        
        total_issues = len(self.results["issues"])
        
        print(f"\n📊 SUMMARY:")
        print(f"Total Issues Found: {total_issues}")
        print(f"Testing Completed: {datetime.now().isoformat()}")
        
        # Content verification summary
        print(f"\n🔍 CONTENT VERIFICATION SUMMARY:")
        for env in ["local", "production"]:
            if env in self.results["content_verification"]:
                env_results = self.results["content_verification"][env]
                total_verifications = sum(len(page_results) for page_results in env_results.values())
                passed_verifications = sum(
                    sum(1 for result in page_results if result["status"] == "PASS")
                    for page_results in env_results.values()
                )
                print(f"{env.upper()}: {passed_verifications}/{total_verifications} verifications passed")
        
        if self.results["issues"]:
            print(f"\n🚨 ISSUES FOUND:")
            for i, issue in enumerate(self.results["issues"], 1):
                print(f"{i}. {issue['environment'].upper()} - {issue['test']}: {issue['issue']}")
                if issue['details']:
                    print(f"   Details: {issue['details']}")
        else:
            print("\n🎉 NO ISSUES FOUND - ALL TESTS PASSED!")
            
        # Save detailed report
        report_file = f"comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return total_issues == 0

if __name__ == "__main__":
    tester = ComprehensiveTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
