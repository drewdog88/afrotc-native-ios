#!/usr/bin/env python3
"""
Test production backup functionality
"""

import sys
import os
sys.path.append('api')

# Use production app configuration
from app import app, db, UniversityContact
from parse_contacts import parse_contact_data

def test_backup_functionality():
    """Test backup functionality in production"""
    print("=== TESTING PRODUCTION BACKUP FUNCTIONALITY ===")
    
    with app.app_context():
        # Check if we have contacts
        contact_count = UniversityContact.query.count()
        print(f"Contacts in database: {contact_count}")
        
        # Test get_backup_files
        from app import get_backup_files
        backup_files = get_backup_files()
        print(f"Current backup files: {len(backup_files)}")
        
        for backup in backup_files:
            print(f"  - {backup['filename']} ({backup['size']} bytes)")
        
        # Create a test backup if none exist
        if not backup_files:
            print("\nNo backups found. Creating a test backup...")
            from app import backup_database
            result = backup_database("Test backup after contact import")
            if result[0]:
                print(f"✓ Created backup: {result[0]}")
                
                # Check again
                backup_files = get_backup_files()
                print(f"Backup files after creation: {len(backup_files)}")
                for backup in backup_files:
                    print(f"  - {backup['filename']} ({backup['size']} bytes)")
            else:
                print("✗ Failed to create backup")
        else:
            print("\nBackups found - system is working correctly!")

if __name__ == "__main__":
    test_backup_functionality()
