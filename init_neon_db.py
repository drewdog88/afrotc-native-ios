#!/usr/bin/env python3
"""
Script to initialize Neon PostgreSQL database with tables and default admin user
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Add the current directory to Python path so we can import from app_local
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def main():
    print("🚀 Initializing Neon PostgreSQL Database...")
    print("=" * 50)
    
    # Import after loading environment variables
    try:
        from app_local import app, db, User
        from werkzeug.security import generate_password_hash
    except ImportError as e:
        print(f"❌ Error importing Flask app: {e}")
        return False
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    print(f"📂 Database URL: {database_url[:50]}...")
    
    try:
        with app.app_context():
            # Check current state
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            print(f"📊 Current tables: {len(existing_tables)} - {existing_tables}")
            
            # Create all tables
            print("🔧 Creating database tables...")
            db.create_all()
            
            # Check again after creation
            inspector = inspect(db.engine)
            new_tables = inspector.get_table_names()
            print(f"✅ Tables after creation: {len(new_tables)} - {new_tables}")
            
            # Create default admin user if it doesn't exist
            existing_admin = User.query.filter_by(username='admin').first()
            if not existing_admin:
                print("👤 Creating default admin user...")
                admin_user = User(
                    username='admin',
                    email='admin@afrotc695.com',
                    password_hash=generate_password_hash('admin123'),
                    role='admin',
                    is_active=True
                )
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Admin user created successfully!")
            else:
                print("ℹ️  Admin user already exists")
            
            # Verify user creation
            user_count = User.query.count()
            print(f"📊 Total users in database: {user_count}")
            
            print("\n🎉 Database initialization completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
