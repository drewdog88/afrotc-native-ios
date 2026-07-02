#!/usr/bin/env python3
"""
Neon PostgreSQL Backup Scheduler for AFROTC 695 Recruitment System
This script runs nightly backups using Vercel Blob storage with 30-day retention.
"""

import os
import sys
import time
import schedule
import threading
from datetime import datetime, timedelta
import json
import requests
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from vercel_blob import put, list as blob_list, delete, head

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and database models
try:
    from api.app import app, db, User, PotentialRecruit, Cadet, UniversityContact, RecruitmentEvent, ExternalLink, RecruitmentDocument, ActivityLog, PasswordHistory
except ImportError:
    print("Error: Could not import Flask app. Make sure you're running from the project root.")
    sys.exit(1)

def get_database_engine():
    """Get database engine for backup operations"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if database_url and database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        if not database_url:
            print("Error: DATABASE_URL environment variable not set")
            return None
            
        engine = create_engine(database_url)
        return engine
    except Exception as e:
        print(f"Error creating database engine: {e}")
        return None

def backup_database_neon(description="Nightly automatic backup"):
    """Create a PostgreSQL database backup with timestamp and description"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"afrotc695_backup_{timestamp}.json"
        
        # Export all data to JSON format
        backup_data = {
            'timestamp': timestamp,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'tables': {}
        }
        
        # Get database engine
        engine = get_database_engine()
        if not engine:
            return None, None
            
        # Export each table
        tables = ['user', 'potential_recruit', 'cadet', 'university_contact', 
                 'recruitment_event', 'external_link', 'recruitment_document', 
                 'activity_log', 'password_history']
        
        with engine.connect() as connection:
            for table_name in tables:
                try:
                    # Use raw SQL to get all data
                    result = connection.execute(text(f'SELECT * FROM "{table_name}"'))
                    rows = [dict(row._mapping) for row in result]
                    backup_data['tables'][table_name] = rows
                    print(f"Backed up {len(rows)} records from {table_name}")
                except Exception as e:
                    print(f"Error backing up table {table_name}: {e}")
                    backup_data['tables'][table_name] = []
        
        # Convert to JSON string
        backup_json = json.dumps(backup_data, indent=2, default=str)
        
        # Upload to Vercel Blob
        blob_response = put(
            backup_filename,
            backup_json.encode('utf-8'),
            {"addRandomSuffix": False}
        )
        
        if blob_response and 'url' in blob_response:
            print(f"Backup uploaded successfully: {backup_filename}")
            return backup_filename, blob_response['url']
        else:
            print("Failed to upload backup to blob storage")
            return None, None
            
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None, None

def list_backup_files():
    """List all backup files in blob storage"""
    try:
        # Use the imported list function directly from vercel_blob
        blob_files = blob_list()
        
        # Handle different response types from vercel_blob
        if hasattr(blob_files, '__iter__') and not isinstance(blob_files, str):
            # It's some kind of iterable (list, tuple, etc.)
            return list(blob_files)
        elif hasattr(blob_files, 'blobs'):
            # If it's an object with a blobs attribute
            return blob_files.blobs
        else:
            print(f"Unexpected response type from blob.list(): {type(blob_files)}")
            return []
    except Exception as e:
        print(f"Error listing backup files: {e}")
        return []

def delete_backup_file(filename):
    """Delete a backup file from blob storage"""
    try:
        delete(filename)
        print(f"Deleted backup file: {filename}")
        return True
    except Exception as e:
        print(f"Error deleting backup file {filename}: {e}")
        return False

def cleanup_old_backups():
    """Clean up backups older than 30 days"""
    try:
        print("Starting backup cleanup...")
        backup_files = list_backup_files()
        
        if not backup_files:
            print("No backup files found")
            return
            
        cutoff_date = datetime.now() - timedelta(days=30)
        deleted_count = 0
        
        for backup_file in backup_files:
            try:
                # Extract timestamp from filename: afrotc695_backup_YYYYMMDD_HHMMSS.json
                filename = backup_file.get('pathname', '') if isinstance(backup_file, dict) else str(backup_file)
                
                if not filename.startswith('afrotc695_backup_') or not filename.endswith('.json'):
                    continue
                    
                # Extract timestamp from filename
                timestamp_str = filename.replace('afrotc695_backup_', '').replace('.json', '')
                backup_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                
                if backup_date < cutoff_date:
                    if delete_backup_file(filename):
                        deleted_count += 1
                        
            except Exception as e:
                print(f"Error processing backup file {filename}: {e}")
                continue
        
        print(f"Cleanup completed: {deleted_count} old backups deleted")
        
    except Exception as e:
        print(f"Error during backup cleanup: {e}")

def perform_nightly_backup():
    """Perform the nightly backup"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] Starting nightly backup...")
    
    try:
        # Create backup with description
        backup_filename, backup_url = backup_database_neon("Nightly automatic backup")
        
        if backup_filename:
            print(f"[{timestamp}] Nightly backup completed successfully: {backup_filename}")
            
            # Clean up old backups (keep last 30 days)
            cleanup_old_backups()
        else:
            print(f"[{timestamp}] Nightly backup failed")
            
    except Exception as e:
        print(f"[{timestamp}] Error during nightly backup: {e}")

def run_backup_scheduler():
    """Run the backup scheduler"""
    print("Starting AFROTC 695 Neon Backup Scheduler...")
    print("Nightly backups will run at 2:00 AM")
    print("Backup retention: 30 days")
    print("Storage: Vercel Blob")
    print("Press Ctrl+C to stop the scheduler")
    
    # Schedule nightly backup at 2:00 AM only
    schedule.every().day.at("02:00").do(perform_nightly_backup)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\nBackup scheduler stopped by user")
    except Exception as e:
        print(f"Error in backup scheduler: {e}")

def run_single_backup():
    """Run a single backup immediately"""
    print("Running immediate backup...")
    perform_nightly_backup()

def test_backup_system():
    """Test the backup system"""
    print("Testing backup system...")
    
    # Test backup creation
    print("1. Testing backup creation...")
    backup_filename, backup_url = backup_database_neon("Test backup")
    if backup_filename:
        print(f"✅ Backup created: {backup_filename}")
    else:
        print("❌ Backup creation failed")
        return
    
    # Test backup listing
    print("2. Testing backup listing...")
    backup_files = list_backup_files()
    print(f"✅ Found {len(backup_files)} backup files")
    
    # Test cleanup
    print("3. Testing cleanup (will not delete recent backups)...")
    cleanup_old_backups()
    print("✅ Cleanup test completed")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--now":
            # Run a single backup immediately
            run_single_backup()
        elif sys.argv[1] == "--test":
            # Test the backup system
            test_backup_system()
        else:
            print("Usage: python neon_backup_scheduler.py [--now|--test]")
            print("  --now: Run a single backup immediately")
            print("  --test: Test the backup system")
    else:
        # Run the scheduled backup system
        run_backup_scheduler()
