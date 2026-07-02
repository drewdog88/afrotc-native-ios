#!/usr/bin/env python3
"""
Local Development Startup Script for AFROTC 695 Recruitment System
This script sets up the local environment to use the same Neon database and Vercel Blob storage as production.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from env.local
load_dotenv('env.local')

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'DATABASE_URL',
        'BLOB_READ_WRITE_TOKEN',
        'SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease check your env.local file and ensure all variables are set.")
        return False
    
    print("✅ All required environment variables are set")
    return True

def test_database_connection():
    """Test the Neon database connection"""
    try:
        from app_local import db, app
        from sqlalchemy import text
        
        with app.app_context():
            # Test database connection
            db.session.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_blob_connection():
    """Test the Vercel Blob connection"""
    try:
        from vercel_blob import list as blob_list
        
        # Test blob connection by listing files
        blobs = blob_list()
        print("✅ Vercel Blob connection successful")
        return True
    except Exception as e:
        print(f"❌ Vercel Blob connection failed: {e}")
        return False

def initialize_database():
    """Initialize the database tables"""
    try:
        from app_local import db, app
        
        with app.app_context():
            db.create_all()
            print("✅ Database tables created successfully")
            return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def main():
    """Main startup function"""
    print("🚀 AFROTC 695 Recruitment System - Local Development Setup")
    print("=" * 60)
    
    # Check environment variables
    if not check_environment():
        sys.exit(1)
    
    # Test database connection
    if not test_database_connection():
        print("\n💡 Troubleshooting tips:")
        print("   - Check your DATABASE_URL in env.local")
        print("   - Ensure your Neon database is accessible")
        print("   - Verify your network connection")
        sys.exit(1)
    
    # Test blob connection
    if not test_blob_connection():
        print("\n💡 Troubleshooting tips:")
        print("   - Check your BLOB_READ_WRITE_TOKEN in env.local")
        print("   - Ensure your Vercel Blob storage is accessible")
        print("   - Verify your network connection")
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        print("\n💡 Troubleshooting tips:")
        print("   - Check your database permissions")
        print("   - Ensure your Neon database is properly configured")
        sys.exit(1)
    
    print("\n🎉 Local development environment is ready!")
    print("\nStarting Flask development server...")
    print("=" * 60)
    
    # Start the Flask app
    from app_local import app
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
