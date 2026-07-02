# AFROTC 695 Recruitment Management System

A modern, cloud-based recruitment management system for AFROTC Detachment 695 at the University of Portland. Built with Flask, deployed on Vercel, and powered by Neon PostgreSQL database.

## 🚀 Project Overview

This web application streamlines and secures the recruitment process for Air Force ROTC Detachment 695. Built with modern cloud technologies, it provides robust tools for tracking potential recruits, managing existing cadets, coordinating with high school contacts, scheduling recruitment events, and maintaining comprehensive activity logs.

## ✨ Key Features

### 📊 **Comprehensive Data Management**
- **Potential Recruit Tracking**: Complete profiles with academic and personal information
- **Cadets Management**: Status tracking (active/inactive/graduated) with unenrollment tracking
- **High School Contact Management**: Extensive contact database with outreach coordination
- **Event Calendar**: Full calendar integration with recruitment event scheduling
- **Materials Library**: Document management with external links and file storage

### 🔍 **Advanced Analytics & Reporting**
- **System Statistics Dashboard**: Real-time system metrics and performance monitoring
- **Database Analytics**: Live database size, table counts, and record distribution
- **User Activity Tracking**: User growth trends, activity patterns, and engagement metrics
- **Recruitment Intelligence**: Event status tracking, recruit progression, cadet analytics
- **Performance Monitoring**: CPU, memory, disk usage with color-coded indicators
- **Activity Logging**: Complete audit trail of all user actions and system changes
- **Export Functionality**: Download data in Excel, PDF, and CSV formats
- **Sortable Tables**: Interactive sorting on all data columns

### 🔐 **Security & Administration**
- **Session-based Authentication**: Secure login system with role-based access control
- **Comprehensive User Management**: Admin and Recruiter roles with full lifecycle management
- **Password Security**: Password history, expiry policies, and complexity requirements
- **Forgot Password System**: Secure password recovery via secret questions
- **Account Locking**: Automatic account locking for security violations
- **Admin Panel**: Comprehensive administrative tools and system monitoring
- **Activity Monitoring**: Detailed logs of user actions, logins, and data changes
- **IP Address Tracking**: Security monitoring with client information logging

### 🎨 **User Experience**
- **Responsive Design**: Bootstrap 5 interface optimized for all devices
- **Dual Theme System**: Toggle between "Original" and "Air Force Standard" themes
- **Official Air Force Branding**: Integrated Air Force logo and color schemes
- **Background Integration**: Custom detachment imagery and branding
- **Intuitive Navigation**: Clean, professional interface with easy data access
- **Real-time Updates**: Live data updates and immediate feedback
- **Interactive Charts**: Chart.js integration for data visualization

### 💾 **Cloud-Based Data Protection**
- **Automated Backups**: Scheduled nightly database backups via Vercel Cron Jobs
- **Cloud Storage**: Vercel Blob storage for secure file management
- **Manual Backup/Restore**: On-demand backup creation and restoration
- **Data Integrity**: Comprehensive backup verification and validation
- **30-Day Retention**: Automatic cleanup of old backups

## 🏗️ Architecture

### **Modern Cloud Stack**
- **Backend**: Python Flask 3.1.1 with SQLAlchemy ORM
- **Database**: Neon PostgreSQL (serverless, auto-scaling)
- **Deployment**: Vercel (serverless functions with edge caching)
- **Storage**: Vercel Blob Storage (secure file management)
- **Scheduling**: Vercel Cron Jobs (serverless task scheduling)
- **Frontend**: HTML5, CSS3, JavaScript with Bootstrap 5
- **Authentication**: Werkzeug password hashing with session management
- **Templates**: Jinja2 templating engine
- **Data Export**: Pandas, OpenPyXL, ReportLab
- **System Monitoring**: psutil for performance metrics
- **Charts & Visualization**: Chart.js with datalabels plugin

### **Database Schema**
- **User Management**: Users, password history, activity logs
- **Recruitment Data**: Potential recruits, cadets, university contacts
- **Event Management**: Recruitment events with calendar integration
- **Materials**: External links, recruitment documents
- **System Data**: Activity logs, system statistics

## 🚀 Quick Start

### **Local Development**

1. **Clone the repository:**
```bash
git clone https://github.com/drewdog88/afrotc695recruitment.git
cd afrotc695recruitment
```

2. **Create virtual environment:**
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
# Copy the example environment file
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize the database:**
```bash
python -c "from api.app import app, db; app.app_context().push(); db.create_all()"
```

6. **Run the application:**
```bash
python app_local.py
```

The application will be available at `http://localhost:5000`

### **Production Deployment**

The application is automatically deployed to Vercel when changes are pushed to the main branch.

**Production URL**: https://afrotc695recruitment.vercel.app

## 📋 Environment Variables

### **Required for Local Development**
```bash
# Database
DATABASE_URL=postgresql://username:password@host:port/database

# Vercel Blob Storage
BLOB_READ_WRITE_TOKEN=your_vercel_blob_token

# Flask
SECRET_KEY=your_secret_key
FLASK_ENV=development
```

### **Production (Vercel)**
Environment variables are configured in the Vercel dashboard and automatically available to the application.

## 🔧 Configuration

### **Database Configuration**
- **Local**: SQLite database for development
- **Production**: Neon PostgreSQL with connection pooling
- **Migrations**: Automatic schema management via SQLAlchemy

### **File Storage**
- **Local**: Local file system for development
- **Production**: Vercel Blob Storage for secure cloud file management
- **Backups**: Automated JSON exports stored in Vercel Blob

### **Scheduling**
- **Local**: Manual execution or local scheduler
- **Production**: Vercel Cron Jobs for automated tasks
- **Backup Schedule**: Nightly at 2:00 AM
- **Cleanup Schedule**: Daily at 3:00 AM

## 📊 System Features

### **Recruitment Management**
- Track potential recruits with comprehensive profiles
- Manage cadet status and progression
- Coordinate with high school and university contacts
- Schedule and track recruitment events
- Export data in multiple formats

### **Administrative Tools**
- User management with role-based access
- System statistics and performance monitoring
- Activity logging and audit trails
- Database backup and restore functionality
- Document and link management

### **Analytics & Reporting**
- Real-time system performance metrics
- User activity and engagement analytics
- Recruitment effectiveness tracking
- Data export capabilities
- Interactive charts and visualizations

## 🔒 Security Features

- **Authentication**: Secure session-based login system
- **Authorization**: Role-based access control (Admin/Recruiter)
- **Password Security**: Hashing, history, expiry policies
- **Activity Logging**: Comprehensive audit trails
- **Data Protection**: Encrypted backups and secure storage
- **Input Validation**: Comprehensive data validation and sanitization

## 🛠️ Development

### **Project Structure**
```
afrotc695recruitment/
├── api/
│   └── app.py              # Main Flask application
├── templates/              # Jinja2 templates
├── static/                 # Static assets (CSS, JS, images)
├── requirements.txt        # Python dependencies
├── vercel.json            # Vercel deployment configuration
├── app_local.py           # Local development server
└── README.md              # This file
```

### **Key Dependencies**
- **Flask 3.1.1**: Web framework
- **Flask-SQLAlchemy 3.1.1**: Database ORM
- **Werkzeug 3.1.3**: Security and utilities
- **vercel-blob 0.4.2**: Cloud file storage
- **psutil 7.0.0**: System monitoring
- **python-docx 1.2.0**: Document processing

### **Database Models**
- **User**: Authentication and user management
- **PotentialRecruit**: Prospective student tracking
- **Cadet**: Current cadet management
- **UniversityContact**: High school and university contacts
- **RecruitmentEvent**: Event scheduling and management
- **ExternalLink**: Materials and resource links
- **RecruitmentDocument**: Document management
- **ActivityLog**: System audit trails

## 🚀 Deployment

### **Vercel Deployment**
The application is automatically deployed to Vercel when changes are pushed to the main branch.

**Features:**
- Serverless functions with automatic scaling
- Edge caching for improved performance
- Automatic HTTPS and CDN distribution
- Environment variable management
- Cron job scheduling for automated tasks

### **Database Management**
- **Neon PostgreSQL**: Serverless, auto-scaling database
- **Connection Pooling**: Optimized database connections
- **Automatic Backups**: Nightly backups with 30-day retention
- **Data Migration**: Seamless schema updates

## 📈 Monitoring & Analytics

### **System Statistics**
- Real-time performance metrics
- Database size and record counts
- User activity patterns
- System resource utilization

### **Activity Logging**
- Comprehensive audit trails
- User action tracking
- Security event monitoring
- Data change logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is proprietary software for AFROTC Detachment 695.

## 🆘 Support

For technical support or questions, please contact the development team.

---

**AFROTC Detachment 695** - University of Portland  
*Empowering the next generation of Air Force leaders* 