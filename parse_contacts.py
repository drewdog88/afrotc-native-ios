#!/usr/bin/env python3
"""
Parse contact data from the Word document and format it for import
"""

import docx
import re

def parse_contact_data():
    """Parse the Word document and extract contact information from tables"""
    
    doc = docx.Document('Jesuit and Catholic High Schools in Seattle and Portland.docx')
    
    contacts = []
    
    # Process each table
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            
            # Skip header rows
            if len(cells) >= 4 and 'School Name' in cells[0]:
                continue
                
            # Process school entries
            if len(cells) >= 4 and cells[0] and cells[0] != 'School Name':
                school_name = cells[0]
                location = cells[1]
                phone = cells[2]
                contact_info = cells[3]
                
                # Parse contact information
                if ':' in contact_info:
                    # Format: "Name (Title): email / phone"
                    contact_parts = contact_info.split(':')
                    contact_name_title = contact_parts[0].strip()
                    email_phone = contact_parts[1].strip()
                    
                    # Extract name and title
                    if '(' in contact_name_title and ')' in contact_name_title:
                        name_match = re.search(r'([^(]+)\s*\(([^)]+)\)', contact_name_title)
                        if name_match:
                            contact_name = name_match.group(1).strip()
                            contact_title = name_match.group(2).strip()
                        else:
                            contact_name = contact_name_title
                            contact_title = 'Contact'
                    else:
                        contact_name = contact_name_title
                        contact_title = 'Contact'
                    
                    # Extract email
                    email = ''
                    if '@' in email_phone:
                        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', email_phone)
                        if email_match:
                            email = email_match.group(1)
                    
                    # Use phone from contact info if available, otherwise use main phone
                    contact_phone = phone
                    if '/' in email_phone:
                        phone_part = email_phone.split('/')[-1].strip()
                        if re.match(r'\(\d{3}\)\s*\d{3}-\d{4}', phone_part):
                            contact_phone = phone_part
                    
                else:
                    # Format: just email
                    contact_name = 'General Office'
                    contact_title = 'General Contact'
                    email = contact_info
                    contact_phone = phone
                
                # Clean up phone number and email
                contact_phone = re.sub(r'\[\d+\]', '', contact_phone).strip()
                email = re.sub(r'\[\d+\]', '', email).strip()
                
                # Determine school type for notes
                school_type = 'Catholic High School'
                if 'Jesuit' in school_name:
                    school_type = 'Jesuit High School'
                elif 'Prep' in school_name:
                    school_type = 'Catholic Preparatory School'
                
                contacts.append({
                    'university_name': school_name,
                    'contact_name': contact_name,
                    'contact_title': contact_title,
                    'email': email,
                    'phone': contact_phone,
                    'address': location,
                    'notes': f'{school_type} - AFROTC Recruitment Contact'
                })
    
    return contacts

def show_import_data():
    """Show what data will be imported"""
    print("=== CONTACT DATA TO BE IMPORTED ===")
    print()
    
    contacts = parse_contact_data()
    
    print(f"Total contacts to import: {len(contacts)}")
    print("\nDetailed contact information:")
    print("-" * 80)
    
    for i, contact in enumerate(contacts, 1):
        print(f"{i}. {contact['university_name']}")
        print(f"   Location: {contact['address']}")
        print(f"   Contact: {contact['contact_name']} ({contact['contact_title']})")
        print(f"   Email: {contact['email']}")
        print(f"   Phone: {contact['phone']}")
        print(f"   Notes: {contact['notes']}")
        print()
    
    return contacts

if __name__ == "__main__":
    show_import_data()
