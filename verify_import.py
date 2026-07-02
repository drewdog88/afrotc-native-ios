#!/usr/bin/env python3
"""
Script to verify data import from SQLite backup to MySQL database
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

def get_mysql_connection():
    """Get MySQL connection using environment variables"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not found in .env file")
        return None
    
    # Create engine
    engine = create_engine(database_url)
    return engine

def check_table_data(engine, table_name):
    """Check data in a MySQL table"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) as count FROM `{table_name}`"))
            count = result.fetchone()[0]
            print(f"{table_name}: {count} records")
            return count
    except Exception as e:
        print(f"Error checking {table_name}: {e}")
        return 0

def main():
    """Main verification function"""
    print("Verifying data import to MySQL database...")
    
    engine = get_mysql_connection()
    if not engine:
        return
    
    tables_to_check = [
        'potential_recruit',
        'cadet', 
        'university_contact',
        'recruitment_event',
        'activity_log',
        'external_link',
        'recruitment_document',
        'user'
    ]
    
    total_records = 0
    
    for table_name in tables_to_check:
        count = check_table_data(engine, table_name)
        total_records += count
    
    print(f"\nTotal records across all tables: {total_records}")
    
    # Show some sample data from cadet table
    print("\nSample cadet data:")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, first_name, last_name, status, graduation_year FROM `cadet` LIMIT 5"))
            for row in result:
                print(f"  ID: {row[0]}, Name: {row[1]} {row[2]}, Status: {row[3]}, Grad Year: {row[4]}")
    except Exception as e:
        print(f"Error showing sample data: {e}")

if __name__ == "__main__":
    main() 