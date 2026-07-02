#!/usr/bin/env python3
"""
AFROTC 695 Recruitment Management System
Startup script for the Flask application
"""

import os
import sys
import subprocess

def main():
    """Main function to start the Flask application"""
    
    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("Warning: Not running in a virtual environment!")
        print("Please activate the virtual environment first:")
        print("  Windows: .venv\\Scripts\\activate")
        print("  macOS/Linux: source .venv/bin/activate")
        print()
    
    # Check if required packages are installed
    try:
        import flask
        import flask_sqlalchemy
        import pandas
        import openpyxl
        import reportlab
        import dotenv
        print("✓ All required packages are installed")
    except ImportError as e:
        print(f"✗ Missing required package: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return 1
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("Creating .env file from env.example...")
        try:
            import shutil
            shutil.copy('env.example', '.env')
            print("✓ .env file created")
        except Exception as e:
            print(f"✗ Failed to create .env file: {e}")
            return 1
    
    # Initialize database if needed
    print("Initializing database...")
    try:
        from app import app, db
        with app.app_context():
            db.create_all()
            print("✓ Database initialized successfully!")
    except Exception as e:
        print(f"Warning: Database initialization issue: {e}")
        print("The application will attempt to create tables on first use.")
    
    # Start the Flask application
    print("Starting AFROTC 695 Recruitment Management System...")
    print("Access the application at: http://localhost:5000")
    print("Default login: admin / admin123")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 