#!/usr/bin/env python3
"""
Run the production import after deployment is complete
This script should be run after the production deployment finishes
"""

import sys
import os
sys.path.append('api')

# Use production app configuration
from app import app, db, UniversityContact
from parse_contacts import parse_contact_data

def main():
    """Run the production import"""
    print("=== PRODUCTION CONTACT IMPORT ===")
    print()
    
    with app.app_context():
        # Drop existing contacts
        deleted_count = UniversityContact.query.delete()
        db.session.commit()
        print(f"Deleted {deleted_count} existing contacts")
        
        # Import new contacts
        contacts = parse_contact_data()
        imported_count = 0
        
        for contact_data in contacts:
            try:
                new_contact = UniversityContact(
                    university_name=contact_data['university_name'],
                    contact_name=contact_data['contact_name'],
                    contact_title=contact_data['contact_title'],
                    email=contact_data['email'],
                    phone=contact_data['phone'],
                    address=contact_data['address'],
                    notes=contact_data['notes']
                )
                db.session.add(new_contact)
                imported_count += 1
                print(f"✓ {contact_data['university_name']}")
            except Exception as e:
                print(f"✗ Error importing {contact_data['university_name']}: {e}")
        
        db.session.commit()
        print(f"\nSuccessfully imported {imported_count} contacts to production")
        
        # Verify
        all_contacts = UniversityContact.query.all()
        print(f"Total contacts in production database: {len(all_contacts)}")

if __name__ == "__main__":
    main()
