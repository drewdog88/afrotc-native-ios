#!/usr/bin/env python3
"""
macOS-specific startup script for AFROTC 695 Recruitment System
Runs on port 5001 to avoid conflicts with macOS AirPlay Receiver on port 5000
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from env.local
load_dotenv('env.local')

def main():
    """Start the application on port 5001"""
    print("🍎 AFROTC 695 Recruitment System - macOS Local Development")
    print("=" * 60)
    print("Starting on port 5001 to avoid AirPlay Receiver conflict...")
    print("Access the application at: http://localhost:5001")
    print("Default login: admin / admin123")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Import and run the app
    from app_local import app, db
    
    with app.app_context():
        db.create_all()
    
    app.run(debug=True, host='0.0.0.0', port=5001)

if __name__ == '__main__':
    main()
