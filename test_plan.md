# AFROTC 695 Test Plan

## Authentication Routes
1. `/` and `/login` (GET, POST)
   - Test successful login with valid credentials
   - Test failed login with invalid credentials
   - Test failed login attempt counting
   - Test account locking after max failed attempts
   - Test redirect to dashboard for authenticated users
   - Test session creation and cookie setting

2. `/logout`
   - Test session clearing
   - Test redirect to login page
   - Test access to protected routes after logout

3. Password Management
   - `/forgot-password` (GET, POST)
   - `/reset-password-question` (GET, POST)
   - `/reset-password` (GET, POST)
   - `/change-password` (GET, POST)
   - Test all password reset flows
   - Test password validation rules
   - Test secret question validation

## Main Application Routes

### Dashboard
- `/dashboard`
  - Test loading of all dashboard components
  - Test data aggregation and statistics
  - Test access control (admin vs regular users)

### Recruit Management
- `/recruits` (GET)
  - Test list view with pagination
  - Test sorting and filtering
  - Test data display format

- `/recruits/add` (GET, POST)
  - Test form validation
  - Test file upload handling
  - Test duplicate detection
  - Test required field validation

- `/api/recruits`
  - Test JSON response format
  - Test data accuracy
  - Test error handling

### Cadet Management
- `/cadet` (GET)
  - Test list view with pagination
  - Test sorting and filtering
  - Test data display format

- `/cadet/add` (GET, POST)
  - Test form validation
  - Test file upload handling
  - Test duplicate detection
  - Test required field validation

- `/cadet/edit/<int:cadet_id>` (GET, POST)
  - Test form pre-population
  - Test update validation
  - Test file handling for updates
  - Test audit trail creation

- `/api/cadet`
  - Test JSON response format
  - Test data accuracy
  - Test error handling

### Contact Management
- `/contacts` (GET)
  - Test list view with pagination
  - Test sorting and filtering
  - Test data display format

- `/contacts/add` (GET, POST)
  - Test form validation
  - Test duplicate detection
  - Test required field validation

- `/contacts/edit/<int:contact_id>` (GET, POST)
  - Test form pre-population
  - Test update validation
  - Test audit trail creation

### Calendar/Event Management
- `/calendar` (GET)
  - Test calendar view rendering
  - Test event display
  - Test date navigation

- `/calendar/add` (GET, POST)
  - Test event creation
  - Test date/time validation
  - Test recurring event handling
  - Test notification settings

### Materials Management
- `/materials` (GET)
  - Test document list view
  - Test link list view
  - Test access control

- Document Operations
  - `/materials/add-document` (GET, POST)
  - `/materials/edit-document/<int:document_id>` (GET, POST)
  - `/materials/delete-document/<int:document_id>` (POST)
  - `/materials/download/<int:document_id>`
  - Test file upload to Vercel Blob
  - Test file download from Vercel Blob
  - Test file deletion from Vercel Blob
  - Test metadata handling
  - Test access control

- Link Operations
  - `/materials/add-link` (GET, POST)
  - `/materials/edit-link/<int:link_id>` (GET, POST)
  - `/materials/delete-link/<int:link_id>` (POST)
  - Test URL validation
  - Test metadata handling
  - Test access control

### Admin Functions
- `/admin` and `/admin/users`
  - Test user list view
  - Test access control

- User Management
  - `/admin/users/add` (GET, POST)
  - `/admin/users/edit/<int:user_id>` (GET, POST)
  - `/admin/users/delete/<int:user_id>` (POST)
  - Test user creation with all fields
  - Test role assignment
  - Test password handling
  - Test duplicate username prevention

- Database Management
  - `/admin/database`
  - `/admin/backup` (GET, POST)
  - `/admin/download-backup/<filename>`
  - `/admin/delete-backup/<filename>` (POST)
  - `/admin/restore` (GET, POST)
  - Test backup creation to Vercel Blob
  - Test backup download from Vercel Blob
  - Test backup deletion from Vercel Blob
  - Test database restore process
  - Test error handling during restore

- Activity Logging
  - `/admin/activity-log`
  - Test log entry creation
  - Test log viewing
  - Test log filtering
  - Test log export

### Data Export Routes
- `/download/recruits/<format>`
- `/download/cadet/<format>`
- `/download/contacts/<format>`
- `/download/activity-log/<format>`
  - Test CSV export
  - Test PDF export
  - Test data accuracy in exports
  - Test file format validity
  - Test large dataset handling

## Profile Management
- `/profile` (GET, POST)
  - Test profile viewing
  - Test profile updating
  - Test password change within profile
  - Test audit trail for profile changes

## Cross-Cutting Concerns
1. Security Testing
   - Test CSRF protection on all forms
   - Test session timeout handling
   - Test access control for all routes
   - Test SQL injection prevention
   - Test XSS prevention
   - Test file upload security

2. Error Handling
   - Test 404 handling
   - Test 500 error handling
   - Test database connection errors
   - Test Blob storage errors
   - Test form validation errors

3. Performance Testing
   - Test page load times
   - Test database query performance
   - Test file upload/download performance
   - Test concurrent user handling

4. UI/UX Testing
   - Test responsive design
   - Test form validation feedback
   - Test error message display
   - Test success message display
   - Test loading indicators

## Test Environment Setup
1. Local Development
   - PostgreSQL database with test data
   - Vercel Blob storage configuration
   - Environment variables setup
   - Virtual environment setup

2. Test Data
   - Create comprehensive test dataset
   - Include edge cases in test data
   - Test data cleanup procedures
