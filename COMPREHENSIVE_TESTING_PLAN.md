# AFROTC 695 Recruitment System - Comprehensive Testing Plan

## Overview
This document defines the complete testing protocol for the AFROTC 695 Recruitment System. **This testing plan MUST be executed after EVERY feature change, deployment, or modification to ensure 100% functionality on both local and production environments.**

## Enhanced Testing Methodology

### Content Verification & Data Accuracy Testing
The comprehensive testing now includes **content verification** that compares what's displayed on pages with actual database data:

#### What Gets Verified:
- **System Statistics**: All displayed numbers match database counts
- **List Pages**: Number of displayed records matches database table counts
- **Data Accuracy**: Specific data fields match database values
- **Recent Activities**: Activity log entries match database records

#### How It Works:
1. **Database Query**: Script queries actual database tables for counts and data
2. **Page Content Extraction**: Uses BeautifulSoup to parse HTML and extract displayed values
3. **Comparison**: Compares database values with displayed values
4. **Reporting**: Detailed report of any mismatches found

#### Example Verification:
- Database has 13 university contacts → Page should display "13" in University Contacts card
- Database has 5 active cadets → Cadet list should show 5 rows
- Recent activity shows 3 login events → Activity table should display 3 rows

This ensures that **what users see is exactly what's in the database** - no more "empty pages" or incorrect statistics!

## Testing Environments
- **Local**: http://localhost:5000 (Flask development server)
- **Production**: https://afrotc695recruitment.vercel.app (Vercel deployment)

## Pre-Testing Setup
1. Ensure local Flask server is running: `python start_local.py`
2. Verify production deployment is live and updated
3. Have test credentials ready for both admin and regular user accounts
4. Clear browser cache and cookies before testing

---

## 1. AUTHENTICATION & SESSION MANAGEMENT

### 1.1 Login Functionality
**Test on both Local and Production**

- [ ] **Login Page Access**
  - [ ] Navigate to `/login` - should return 200
  - [ ] Verify login form is present with username/password fields
  - [ ] Check that form submits to POST `/login`

- [ ] **Valid Login**
  - [ ] Login with valid admin credentials
  - [ ] Login with valid regular user credentials
  - [ ] Verify redirect to dashboard after successful login
  - [ ] Check session is established

- [ ] **Invalid Login**
  - [ ] Attempt login with invalid username
  - [ ] Attempt login with invalid password
  - [ ] Attempt login with empty fields
  - [ ] Verify appropriate error messages display

- [ ] **Logout Functionality**
  - [ ] Click logout link/button
  - [ ] Verify redirect to login page
  - [ ] Verify session is destroyed
  - [ ] Attempt to access protected pages after logout

### 1.2 Password Management
- [ ] **Forgot Password**
  - [ ] Navigate to `/forgot-password`
  - [ ] Submit with valid email
  - [ ] Submit with invalid email
  - [ ] Verify appropriate responses

- [ ] **Password Reset**
  - [ ] Complete password reset flow
  - [ ] Verify new password works
  - [ ] Verify old password no longer works

- [ ] **Change Password**
  - [ ] Navigate to `/change-password` (authenticated)
  - [ ] Submit with current password
  - [ ] Submit with incorrect current password
  - [ ] Verify password change success

### 1.3 2FA Authentication (if enabled)
- [ ] **2FA Setup**
  - [ ] Navigate to `/setup-2fa`
  - [ ] Complete QR code setup
  - [ ] Verify backup codes generation

- [ ] **2FA Verification**
  - [ ] Login with 2FA enabled
  - [ ] Enter correct TOTP code
  - [ ] Enter incorrect TOTP code
  - [ ] Use backup codes

---

## 2. MAIN NAVIGATION & PAGES

### 2.1 Public Pages (Unauthenticated)
- [ ] **Homepage (`/`)**
  - [ ] Verify redirect to login (302)
  - [ ] Check no sensitive data exposed

### 2.2 Protected Pages (Authenticated)
- [ ] **Dashboard (`/dashboard`)**
  - [ ] Verify page loads (200)
  - [ ] Check chart rendering (if authenticated)
  - [ ] Verify statistics display
  - [ ] Test all dashboard links

- [ ] **Recruits (`/recruits`)**
  - [ ] Verify page loads (200)
  - [ ] Check recruit list displays
  - [ ] Test search functionality
  - [ ] Test filtering options
  - [ ] Verify pagination (if applicable)

- [ ] **Contacts (`/contacts`)**
  - [ ] Verify page loads (200)
  - [ ] Check contact list displays
  - [ ] Test search functionality
  - [ ] Test filtering options

- [ ] **Calendar (`/calendar`)**
  - [ ] Verify page loads (200)
  - [ ] Check calendar displays
  - [ ] Test event display
  - [ ] Verify date navigation

- [ ] **Materials (`/materials`)**
  - [ ] Verify page loads (200)
  - [ ] Check external links display
  - [ ] Check documents display
  - [ ] Test sorting functionality

- [ ] **Profile (`/profile`)**
  - [ ] Verify page loads (200)
  - [ ] Check user information displays
  - [ ] Test profile editing

---

## 3. DATA MANAGEMENT - RECRUITS

### 3.1 Recruit List Operations
- [ ] **View Recruits**
  - [ ] Navigate to `/recruits`
  - [ ] Verify all recruits display
  - [ ] Test search by name
  - [ ] Test search by email
  - [ ] Test search by school
  - [ ] Test status filtering
  - [ ] Test school type filtering

### 3.2 Add Recruit
- [ ] **Add Recruit Form**
  - [ ] Navigate to `/recruits/add`
  - [ ] Verify form loads (200)
  - [ ] Test all form fields:
    - [ ] First Name (required)
    - [ ] Last Name (required)
    - [ ] Email
    - [ ] Phone
    - [ ] Major
    - [ ] Current School (required)
    - [ ] School Type (required)
    - [ ] Graduation Year
    - [ ] GPA
    - [ ] SAT Score
    - [ ] ACT Score
    - [ ] Interests
    - [ ] Notes
    - [ ] Status

- [ ] **Form Validation**
  - [ ] Submit with required fields only
  - [ ] Submit with all fields filled
  - [ ] Submit with invalid email
  - [ ] Submit with invalid phone
  - [ ] Submit with invalid GPA
  - [ ] Submit with invalid SAT/ACT scores
  - [ ] Submit with empty required fields

- [ ] **Form Submission**
  - [ ] Submit valid form
  - [ ] Verify redirect to recruits list
  - [ ] Verify new recruit appears in list
  - [ ] Verify data is saved correctly

### 3.3 Edit Recruit
- [ ] **Edit Recruit Form**
  - [ ] Navigate to `/recruits/edit/<id>`
  - [ ] Verify form loads with existing data
  - [ ] Test editing each field
  - [ ] Test form validation
  - [ ] Submit changes
  - [ ] Verify changes are saved

### 3.4 Delete Recruit
- [ ] **Delete Confirmation**
  - [ ] Click delete button
  - [ ] Verify confirmation dialog
  - [ ] Confirm deletion
  - [ ] Verify recruit is removed from list

### 3.5 Export Recruits
- [ ] **CSV Export**
  - [ ] Navigate to `/download/recruits/csv`
  - [ ] Verify file downloads
  - [ ] Verify CSV format is correct
  - [ ] Verify all data is included

- [ ] **Excel Export**
  - [ ] Navigate to `/download/recruits/excel`
  - [ ] Verify file downloads
  - [ ] Verify Excel format is correct
  - [ ] Verify all data is included

- [ ] **PDF Export**
  - [ ] Navigate to `/download/recruits/pdf`
  - [ ] Verify file downloads
  - [ ] Verify PDF format is correct
  - [ ] Verify all data is included

---

## 4. DATA MANAGEMENT - CADETS

### 4.1 Cadet List Operations
- [ ] **View Cadets**
  - [ ] Navigate to `/cadet`
  - [ ] Verify all cadets display
  - [ ] Test search functionality
  - [ ] Test filtering options

### 4.2 Add Cadet
- [ ] **Add Cadet Form**
  - [ ] Navigate to `/cadet/add`
  - [ ] Verify form loads (200)
  - [ ] Test all form fields:
    - [ ] First Name (required)
    - [ ] Last Name (required)
    - [ ] Email (required, unique)
    - [ ] Phone
    - [ ] Major (required)
    - [ ] Graduation Year (required)
    - [ ] Cadet Rank (required)
    - [ ] Hometown
    - [ ] Officer Interest
    - [ ] Status
    - [ ] GPA
    - [ ] Unenrollment Reason
    - [ ] Unenrollment Date

- [ ] **Form Validation**
  - [ ] Submit with required fields only
  - [ ] Submit with all fields filled
  - [ ] Submit with duplicate email
  - [ ] Submit with invalid email
  - [ ] Submit with invalid graduation year
  - [ ] Submit with empty required fields

- [ ] **Form Submission**
  - [ ] Submit valid form
  - [ ] Verify redirect to cadet list
  - [ ] Verify new cadet appears in list
  - [ ] Verify data is saved correctly

### 4.3 Edit Cadet
- [ ] **Edit Cadet Form**
  - [ ] Navigate to `/cadet/edit/<id>`
  - [ ] Verify form loads with existing data
  - [ ] Test editing each field
  - [ ] Test form validation
  - [ ] Submit changes
  - [ ] Verify changes are saved

### 4.4 Export Cadets
- [ ] **CSV Export**
  - [ ] Navigate to `/download/cadet/csv`
  - [ ] Verify file downloads correctly

- [ ] **Excel Export**
  - [ ] Navigate to `/download/cadet/excel`
  - [ ] Verify file downloads correctly

- [ ] **PDF Export**
  - [ ] Navigate to `/download/cadet/pdf`
  - [ ] Verify file downloads correctly

---

## 5. DATA MANAGEMENT - CONTACTS

### 5.1 Contact List Operations
- [ ] **View Contacts**
  - [ ] Navigate to `/contacts`
  - [ ] Verify all contacts display
  - [ ] Test search functionality
  - [ ] Test filtering options

### 5.2 Add Contact
- [ ] **Add Contact Form**
  - [ ] Navigate to `/contacts/add`
  - [ ] Verify form loads (200)
  - [ ] Test all form fields:
    - [ ] University Name (required)
    - [ ] Contact Name (required)
    - [ ] Contact Title
    - [ ] Email (required)
    - [ ] Phone
    - [ ] Address
    - [ ] Notes

- [ ] **Form Validation**
  - [ ] Submit with required fields only
  - [ ] Submit with all fields filled
  - [ ] Submit with invalid email
  - [ ] Submit with empty required fields

- [ ] **Form Submission**
  - [ ] Submit valid form
  - [ ] Verify redirect to contacts list
  - [ ] Verify new contact appears in list
  - [ ] Verify data is saved correctly

### 5.3 Edit Contact
- [ ] **Edit Contact Form**
  - [ ] Navigate to `/contacts/edit/<id>`
  - [ ] Verify form loads with existing data
  - [ ] Test editing each field
  - [ ] Test form validation
  - [ ] Submit changes
  - [ ] Verify changes are saved

### 5.4 Export Contacts
- [ ] **CSV Export**
  - [ ] Navigate to `/download/contacts/csv`
  - [ ] Verify file downloads correctly

- [ ] **Excel Export**
  - [ ] Navigate to `/download/contacts/excel`
  - [ ] Verify file downloads correctly

- [ ] **PDF Export**
  - [ ] Navigate to `/download/contacts/pdf`
  - [ ] Verify file downloads correctly

---

## 6. CALENDAR & EVENTS

### 6.1 Calendar Display
- [ ] **Calendar Page**
  - [ ] Navigate to `/calendar`
  - [ ] Verify calendar displays
  - [ ] Test month navigation
  - [ ] Test year navigation
  - [ ] Verify events display on correct dates

### 6.2 Add Event
- [ ] **Add Event Form**
  - [ ] Navigate to `/calendar/add`
  - [ ] Verify form loads (200)
  - [ ] Test all form fields:
    - [ ] Title (required)
    - [ ] Description
    - [ ] Event Date (required)
    - [ ] Start Time
    - [ ] End Time
    - [ ] Location
    - [ ] University Contact
    - [ ] Event Type (required)
    - [ ] Notes

- [ ] **Form Validation**
  - [ ] Submit with required fields only
  - [ ] Submit with all fields filled
  - [ ] Submit with invalid date
  - [ ] Submit with end time before start time
  - [ ] Submit with empty required fields

- [ ] **Form Submission**
  - [ ] Submit valid form
  - [ ] Verify redirect to calendar
  - [ ] Verify new event appears on calendar
  - [ ] Verify data is saved correctly

---

## 7. MATERIALS MANAGEMENT

### 7.1 External Links
- [ ] **View Links**
  - [ ] Navigate to `/materials`
  - [ ] Verify external links display
  - [ ] Test link categorization
  - [ ] Test sorting functionality

- [ ] **Add External Link**
  - [ ] Navigate to `/materials/add-link`
  - [ ] Verify form loads (200)
  - [ ] Test all form fields:
    - [ ] Title (required)
    - [ ] URL (required)
    - [ ] Description
    - [ ] Category
    - [ ] Sort Order

- [ ] **Form Validation**
  - [ ] Submit with required fields only
  - [ ] Submit with all fields filled
  - [ ] Submit with invalid URL
  - [ ] Submit with empty required fields

- [ ] **Form Submission**
  - [ ] Submit valid form
  - [ ] Verify redirect to materials page
  - [ ] Verify new link appears in list
  - [ ] Verify data is saved correctly

- [ ] **Edit External Link**
  - [ ] Navigate to `/materials/edit-link/<id>`
  - [ ] Verify form loads with existing data
  - [ ] Test editing each field
  - [ ] Submit changes
  - [ ] Verify changes are saved

- [ ] **Delete External Link**
  - [ ] Click delete button
  - [ ] Verify confirmation dialog
  - [ ] Confirm deletion
  - [ ] Verify link is removed from list

### 7.2 Documents
- [ ] **View Documents**
  - [ ] Navigate to `/materials`
  - [ ] Verify documents display
  - [ ] Test document categorization
  - [ ] Test sorting functionality

- [ ] **Add Document**
  - [ ] Navigate to `/materials/add-document`
  - [ ] Verify form loads (200)
  - [ ] Test all form fields:
    - [ ] Title (required)
    - [ ] Description
    - [ ] File upload (required)
    - [ ] Category
    - [ ] Sort Order

- [ ] **File Upload Testing**
  - [ ] Upload PDF file
  - [ ] Upload Word document
  - [ ] Upload PowerPoint file
  - [ ] Upload image file
  - [ ] Attempt upload with invalid file type
  - [ ] Attempt upload with file too large
  - [ ] Verify file is stored in Vercel Blob

- [ ] **Form Validation**
  - [ ] Submit with required fields only
  - [ ] Submit with all fields filled
  - [ ] Submit without file
  - [ ] Submit with empty required fields

- [ ] **Form Submission**
  - [ ] Submit valid form
  - [ ] Verify redirect to materials page
  - [ ] Verify new document appears in list
  - [ ] Verify file is accessible

- [ ] **Download Document**
  - [ ] Click download link
  - [ ] Verify file downloads correctly
  - [ ] Verify file content is correct

- [ ] **Edit Document**
  - [ ] Navigate to `/materials/edit-document/<id>`
  - [ ] Verify form loads with existing data
  - [ ] Test editing each field
  - [ ] Submit changes
  - [ ] Verify changes are saved

- [ ] **Delete Document**
  - [ ] Click delete button
  - [ ] Verify confirmation dialog
  - [ ] Confirm deletion
  - [ ] Verify document is removed from list
  - [ ] Verify file is deleted from Vercel Blob

---

## 8. ADMIN PANEL

### 8.1 Admin Access
- [ ] **Admin Dashboard**
  - [ ] Navigate to `/admin` (admin user)
  - [ ] Verify admin dashboard loads (200)
  - [ ] Check all admin links are present
  - [ ] Verify regular user cannot access (403/redirect)

### 8.2 User Management
- [ ] **User List**
  - [ ] Navigate to `/admin/users`
  - [ ] Verify all users display
  - [ ] Test search functionality
  - [ ] Test filtering options

- [ ] **Add User**
  - [ ] Navigate to `/admin/users/add`
  - [ ] Verify form loads (200)
  - [ ] Test all form fields:
    - [ ] Username (required, unique)
    - [ ] Email (required, unique)
    - [ ] Password (required)
    - [ ] First Name (required)
    - [ ] Last Name (required)
    - [ ] Phone
    - [ ] Role (admin/recruiter)
    - [ ] Secret Question (required)
    - [ ] Secret Answer (required)

- [ ] **Form Validation**
  - [ ] Submit with required fields only
  - [ ] Submit with all fields filled
  - [ ] Submit with duplicate username
  - [ ] Submit with duplicate email
  - [ ] Submit with invalid email
  - [ ] Submit with weak password
  - [ ] Submit with empty required fields

- [ ] **Form Submission**
  - [ ] Submit valid form
  - [ ] Verify redirect to user list
  - [ ] Verify new user appears in list
  - [ ] Verify data is saved correctly

- [ ] **Edit User**
  - [ ] Navigate to `/admin/users/edit/<id>`
  - [ ] Verify form loads with existing data
  - [ ] Test editing each field
  - [ ] Test password change
  - [ ] Submit changes
  - [ ] Verify changes are saved

- [ ] **Delete User**
  - [ ] Click delete button
  - [ ] Verify confirmation dialog
  - [ ] Confirm deletion
  - [ ] Verify user is removed from list

- [ ] **2FA Management**
  - [ ] Enable 2FA for user
  - [ ] Disable 2FA for user
  - [ ] Verify 2FA status changes

### 8.3 Database Management
- [ ] **Database Dashboard**
  - [ ] Navigate to `/admin/database`
  - [ ] Verify database statistics display
  - [ ] Check table information
  - [ ] Verify backup options

- [ ] **Backup Operations**
  - [ ] Create manual backup
  - [ ] Verify backup is created
  - [ ] List backup files
  - [ ] Download backup file
  - [ ] Delete backup file

- [ ] **Restore Operations**
  - [ ] Upload backup file
  - [ ] Verify restore process
  - [ ] Verify data is restored correctly

### 8.4 Activity Log
- [ ] **Activity Log View**
  - [ ] Navigate to `/admin/activity-log`
  - [ ] Verify activity log displays
  - [ ] Test filtering by user
  - [ ] Test filtering by action
  - [ ] Test date range filtering

- [ ] **Export Activity Log**
  - [ ] Navigate to `/download/activity-log/csv`
  - [ ] Verify file downloads correctly

- [ ] **Excel Export**
  - [ ] Navigate to `/download/activity-log/excel`
  - [ ] Verify file downloads correctly

- [ ] **PDF Export**
  - [ ] Navigate to `/download/activity-log/pdf`
  - [ ] Verify file downloads correctly

### 8.5 System Statistics
- [ ] **System Statistics**
  - [ ] Navigate to `/admin/system-statistics`
  - [ ] Verify page loads (200)
  - [ ] **VERIFY SPECIFIC DATA DISPLAYS:**
    - [ ] Total Users card shows number > 0
    - [ ] Active Users card shows number >= 0
    - [ ] Admin Users card shows number > 0
    - [ ] Recent Logins card shows number >= 0
    - [ ] Total Recruits card shows number >= 0
    - [ ] Total Cadets card shows number >= 0
    - [ ] Total Contacts card shows number >= 0
    - [ ] Total Events card shows number >= 0
  - [ ] **VERIFY RECENT ACTIVITY TABLE:**
    - [ ] Table displays recent activities
    - [ ] Activities show correct timestamps
    - [ ] Activities show correct usernames
    - [ ] Activities show correct actions
  - [ ] **VERIFY DATA ACCURACY:**
    - [ ] Compare displayed counts with actual database counts
    - [ ] Verify recent activities match actual log entries

### 8.6 Code Coverage
- [ ] **Code Coverage**
  - [ ] Navigate to `/admin/code-coverage`
  - [ ] Verify coverage page loads
  - [ ] Run coverage analysis
  - [ ] Verify results display

### 8.7 Quality Analysis
- [ ] **Quality Analysis**
  - [ ] Navigate to `/admin/quality-analysis`
  - [ ] Verify analysis page loads
  - [ ] Run quality analysis
  - [ ] Verify results display

### 8.8 Vulnerability Scan
- [ ] **Vulnerability Scan**
  - [ ] Navigate to `/admin/vulnerability-scan`
  - [ ] Verify scan page loads
  - [ ] Run vulnerability scan
  - [ ] Verify results display

---

## 9. API ENDPOINTS

### 9.1 Public APIs
- [ ] **Recruits API**
  - [ ] Navigate to `/api/recruits`
  - [ ] Verify JSON response
  - [ ] Check data structure
  - [ ] Verify authentication requirements

- [ ] **Cadets API**
  - [ ] Navigate to `/api/cadet`
  - [ ] Verify JSON response
  - [ ] Check data structure
  - [ ] Verify authentication requirements

---

## 10. ERROR HANDLING

### 10.1 HTTP Error Pages
- [ ] **404 Error**
  - [ ] Navigate to non-existent page
  - [ ] Verify 404 page displays
  - [ ] Check error page styling

- [ ] **403 Error**
  - [ ] Attempt to access admin as regular user
  - [ ] Verify 403 page displays
  - [ ] Check error page styling

- [ ] **500 Error**
  - [ ] Trigger server error (if possible)
  - [ ] Verify 500 page displays
  - [ ] Check error page styling

### 10.2 Form Error Handling
- [ ] **Validation Errors**
  - [ ] Submit forms with invalid data
  - [ ] Verify error messages display
  - [ ] Check error message styling
  - [ ] Verify form data is preserved

---

## 11. PERFORMANCE & RESPONSIVENESS

### 11.1 Page Load Times
- [ ] **Homepage Load**
  - [ ] Measure load time
  - [ ] Verify under 3 seconds

- [ ] **Dashboard Load**
  - [ ] Measure load time
  - [ ] Verify under 3 seconds

- [ ] **Data Pages Load**
  - [ ] Measure load time for large datasets
  - [ ] Verify under 5 seconds

### 11.2 Responsive Design
- [ ] **Mobile View**
  - [ ] Test on mobile viewport
  - [ ] Verify navigation works
  - [ ] Check form usability
  - [ ] Verify charts display correctly

- [ ] **Tablet View**
  - [ ] Test on tablet viewport
  - [ ] Verify layout adapts
  - [ ] Check functionality

- [ ] **Desktop View**
  - [ ] Test on desktop viewport
  - [ ] Verify full functionality
  - [ ] Check all features accessible

---

## 12. BROWSER COMPATIBILITY

### 12.1 Modern Browsers
- [ ] **Chrome**
  - [ ] Test all functionality
  - [ ] Verify no console errors
  - [ ] Check responsive design

- [ ] **Firefox**
  - [ ] Test all functionality
  - [ ] Verify no console errors
  - [ ] Check responsive design

- [ ] **Safari**
  - [ ] Test all functionality
  - [ ] Verify no console errors
  - [ ] Check responsive design

- [ ] **Edge**
  - [ ] Test all functionality
  - [ ] Verify no console errors
  - [ ] Check responsive design

---

## 13. SECURITY TESTING

### 13.1 Authentication Security
- [ ] **Session Management**
  - [ ] Test session timeout
  - [ ] Verify logout destroys session
  - [ ] Check session hijacking protection

- [ ] **Access Control**
  - [ ] Verify admin-only pages require admin role
  - [ ] Test direct URL access to protected pages
  - [ ] Verify proper redirects for unauthorized access

### 13.2 Input Validation
- [ ] **SQL Injection**
  - [ ] Test search fields with SQL injection attempts
  - [ ] Test form fields with malicious input
  - [ ] Verify no SQL errors are exposed

- [ ] **XSS Protection**
  - [ ] Test form fields with script tags
  - [ ] Verify scripts are not executed
  - [ ] Check output encoding

### 13.3 File Upload Security
- [ ] **File Type Validation**
  - [ ] Attempt upload of executable files
  - [ ] Attempt upload of script files
  - [ ] Verify only allowed file types are accepted

- [ ] **File Size Limits**
  - [ ] Attempt upload of very large files
  - [ ] Verify size limits are enforced

---

## 14. DATA INTEGRITY

### 14.1 Database Operations
- [ ] **Data Persistence**
  - [ ] Create test records
  - [ ] Verify data is saved correctly
  - [ ] Restart application
  - [ ] Verify data persists

- [ ] **Data Relationships**
  - [ ] Test foreign key relationships
  - [ ] Verify cascade operations
  - [ ] Check data consistency

### 14.2 Export Data Accuracy
- [ ] **CSV Export Accuracy**
  - [ ] Export data
  - [ ] Compare with database records
  - [ ] Verify all fields are included
  - [ ] Check data formatting

- [ ] **Excel Export Accuracy**
  - [ ] Export data
  - [ ] Open in Excel
  - [ ] Verify data integrity
  - [ ] Check formatting

- [ ] **PDF Export Accuracy**
  - [ ] Export data
  - [ ] Open PDF
  - [ ] Verify data integrity
  - [ ] Check formatting

---

## 15. INTEGRATION TESTING

### 15.1 Vercel Blob Integration
- [ ] **File Upload**
  - [ ] Upload document
  - [ ] Verify file is stored in Vercel Blob
  - [ ] Verify file is accessible via URL

- [ ] **File Download**
  - [ ] Download uploaded file
  - [ ] Verify file content is correct
  - [ ] Verify file size matches

- [ ] **File Deletion**
  - [ ] Delete file from application
  - [ ] Verify file is removed from Vercel Blob
  - [ ] Verify file is no longer accessible

### 15.2 Neon Database Integration
- [ ] **Database Connection**
  - [ ] Verify connection to Neon database
  - [ ] Test read operations
  - [ ] Test write operations
  - [ ] Test transaction handling

- [ ] **Database Backup**
  - [ ] Create backup
  - [ ] Verify backup is stored correctly
  - [ ] Test backup restoration

---

## 16. REGRESSION TESTING

### 16.1 Previous Issues
- [ ] **Chart Rendering**
  - [ ] Verify dashboard charts display correctly
  - [ ] Check for CSP-related errors
  - [ ] Verify Chart.js loads properly

- [ ] **Form Functionality**
  - [ ] Test all forms work correctly
  - [ ] Verify no csrf_token errors
  - [ ] Check form submission success

- [ ] **Export Functionality**
  - [ ] Test all export formats
  - [ ] Verify files download correctly
  - [ ] Check export data accuracy

---

## TESTING EXECUTION CHECKLIST

### Before Testing
- [ ] Local Flask server is running
- [ ] Production deployment is updated
- [ ] Test credentials are available
- [ ] Browser cache is cleared
- [ ] Testing environment is prepared

### During Testing
- [ ] Execute each section systematically
- [ ] Document any failures or issues
- [ ] Take screenshots of errors
- [ ] Note browser console errors
- [ ] Record performance metrics

### After Testing
- [ ] Compile test results
- [ ] Document all issues found
- [ ] Create bug reports for failures
- [ ] Update Taskmaster with issues
- [ ] Plan fixes for identified problems

---

## ISSUE TRACKING

### Issue Categories
1. **Critical**: Application crashes, data loss, security vulnerabilities
2. **High**: Major functionality broken, user workflow blocked
3. **Medium**: Minor functionality issues, UI problems
4. **Low**: Cosmetic issues, minor improvements

### Issue Documentation
For each issue found:
- [ ] Screenshot of the problem
- [ ] Steps to reproduce
- [ ] Expected vs actual behavior
- [ ] Browser and version
- [ ] Environment (local/production)
- [ ] Error messages or console output

---

## COMPLETION CRITERIA

Testing is complete when:
- [ ] All test cases pass on both local and production
- [ ] No critical or high-priority issues remain
- [ ] All functionality works as expected
- [ ] Performance meets requirements
- [ ] Security requirements are met
- [ ] Documentation is updated

---

**This testing plan MUST be executed after EVERY feature change, deployment, or modification to ensure 100% functionality on both local and production environments.**
