# 🏠 Local Development Guide

This guide explains how to set up and run the AFROTC 695 Recruitment System locally using the same Neon database and Vercel Blob storage as production.

## 🎯 Overview

The local development environment is designed to use the **exact same code paths** as the Vercel production environment, ensuring consistency between development and production. The main differences are:

- **Local Flask server** instead of Vercel serverless functions
- **Same database** (Neon PostgreSQL) as production
- **Same file storage** (Vercel Blob) as production
- **Same environment variables** structure

## 📋 Prerequisites

1. **Python 3.8+** installed on your system
2. **Neon PostgreSQL database** (same as production)
3. **Vercel Blob storage** (same as production)
4. **Environment variables** configured

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install local development dependencies
pip install -r requirements_local.txt
```

### 2. Configure Environment Variables

Copy the example environment file and update it with your credentials:

```bash
# Copy the example environment file
cp env.local.example env.local

# Edit env.local with your actual credentials
# Make sure to include:
# - DATABASE_URL (from Neon)
# - BLOB_READ_WRITE_TOKEN (from Vercel)
# - SECRET_KEY (for Flask sessions)
```

### 3. Start Local Development Server

```bash
# Use the automated startup script (recommended)
python start_local.py

# Or run directly
python app_local.py
```

The application will be available at `http://localhost:5000`

## 🔧 Configuration Details

### Environment Variables (`env.local`)

```bash
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-super-secret-key-change-this-in-production

# Neon PostgreSQL Database (same as production)
DATABASE_URL=postgresql://neondb_owner:PASSWORD@HOST.neon.tech/neondb?sslmode=require

# Vercel Blob Storage (same as production)
BLOB_READ_WRITE_TOKEN=vercel_blob_rw_REPLACE_WITH_YOUR_TOKEN

# Additional configuration...
```

### Database Configuration

The local environment uses the same Neon PostgreSQL database as production:

- **Connection pooling**: Configured for serverless compatibility
- **SSL**: Required for Neon connections
- **NullPool**: Used to prevent connection pooling issues in development

### File Storage

All file uploads and downloads use Vercel Blob storage:

- **Uploads**: Files are stored in Vercel Blob with timestamps
- **Downloads**: Files are served directly from Vercel Blob URLs
- **Backups**: Database backups are stored in Vercel Blob

## 📁 File Structure

```
afrotc695recruitment/
├── api/
│   └── app.py              # Vercel production app
├── app_local.py            # Local development app
├── start_local.py          # Local startup script
├── env.local               # Local environment variables
├── requirements_local.txt  # Local dependencies
├── templates/              # HTML templates (shared)
├── static/                 # Static assets (shared)
└── LOCAL_DEVELOPMENT.md    # This file
```

## 🔄 Development Workflow

### Code Changes

1. **Make changes** in `app_local.py` for testing
2. **Test thoroughly** in local environment
3. **Copy changes** to `api/app.py` for production
4. **Deploy** to Vercel

### Database Changes

1. **Local testing**: Use `app_local.py` to test database changes
2. **Production**: Same database is used, so changes are immediately available
3. **Migrations**: Use SQLAlchemy's `db.create_all()` for schema changes

### File Upload Testing

1. **Upload files** through the local interface
2. **Verify storage** in Vercel Blob dashboard
3. **Test downloads** from both local and production URLs

## 🛠️ Troubleshooting

### Database Connection Issues

```bash
# Check if DATABASE_URL is set correctly
echo $DATABASE_URL

# Test database connection
python -c "
from app_local import db, app
with app.app_context():
    db.engine.execute('SELECT 1')
    print('Database connection successful')
"
```

### Blob Storage Issues

```bash
# Check if BLOB_READ_WRITE_TOKEN is set
echo $BLOB_READ_WRITE_TOKEN

# Test blob connection
python -c "
from vercel_blob import list
blobs = list()
print('Blob connection successful')
"
```

### Common Issues

1. **Import errors**: Make sure all dependencies are installed
2. **Connection timeouts**: Check your internet connection
3. **Permission errors**: Verify your API tokens are correct
4. **Port conflicts**: Change the port in `app_local.py` if needed

## 🔒 Security Considerations

### Local Development Security

- **Environment variables**: Never commit `env.local` to version control
- **API tokens**: Keep your Neon and Vercel tokens secure
- **Debug mode**: Only use debug mode in local development
- **HTTPS**: Local development uses HTTP (production uses HTTPS)

### Data Privacy

- **Same database**: Local development uses the same database as production
- **PII handling**: Be careful with sensitive data in development
- **Testing**: Use test data when possible

## 📚 Additional Resources

- [Neon PostgreSQL Documentation](https://neon.tech/docs)
- [Vercel Blob Documentation](https://vercel.com/docs/storage/vercel-blob)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

## 🤝 Contributing

When contributing to the project:

1. **Use local environment** for development and testing
2. **Test thoroughly** before copying changes to production
3. **Follow the same patterns** as the production code
4. **Update documentation** if needed

## 📞 Support

If you encounter issues with the local development environment:

1. Check the troubleshooting section above
2. Verify your environment variables are correct
3. Ensure all dependencies are installed
4. Check the logs for specific error messages
