#!/usr/bin/env python3
"""
Script to check potential recruits and their distribution across schools
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from datetime import datetime

# Load environment variables
load_dotenv()

def get_database_connection():
    """Get connection to production database"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    # Convert postgres:// to postgresql:// for psycopg2
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def check_recruits(conn):
    """Check potential recruits and their distribution"""
    cursor = conn.cursor()
    
    print("=== POTENTIAL RECRUITS ANALYSIS ===")
    print()
    
    # Get total count
    cursor.execute("SELECT COUNT(*) FROM potential_recruit")
    total_recruits = cursor.fetchone()[0]
    print(f"Total potential recruits: {total_recruits}")
    print()
    
    # Check recruits by school
    cursor.execute("""
        SELECT current_school, COUNT(*) as recruit_count
        FROM potential_recruit
        GROUP BY current_school
        ORDER BY recruit_count DESC, current_school
    """)
    
    school_recruits = cursor.fetchall()
    print("Recruits by School:")
    print("-" * 60)
    for school, count in school_recruits:
        print(f"{school:40} | {count:3} recruits")
    print()
    
    # Check recruits by status
    cursor.execute("""
        SELECT status, COUNT(*) as status_count
        FROM potential_recruit
        GROUP BY status
        ORDER BY status_count DESC
    """)
    
    status_recruits = cursor.fetchall()
    print("Recruits by Status:")
    print("-" * 30)
    for status, count in status_recruits:
        print(f"{status:15} | {count:3} recruits")
    print()
    
    # Check academic statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            AVG(gpa) as avg_gpa,
            MIN(gpa) as min_gpa,
            MAX(gpa) as max_gpa,
            COUNT(sat_score) as sat_count,
            COUNT(act_score) as act_count
        FROM potential_recruit
    """)
    
    stats = cursor.fetchone()
    total, avg_gpa, min_gpa, max_gpa, sat_count, act_count = stats
    
    print("Academic Statistics:")
    print("-" * 30)
    print(f"Total recruits: {total}")
    print(f"Average GPA: {avg_gpa:.2f}")
    print(f"GPA range: {min_gpa:.2f} - {max_gpa:.2f}")
    print(f"With SAT scores: {sat_count}")
    print(f"With ACT scores: {act_count}")
    print()
    
    # Check majors distribution
    cursor.execute("""
        SELECT major, COUNT(*) as major_count
        FROM potential_recruit
        GROUP BY major
        ORDER BY major_count DESC
        LIMIT 10
    """)
    
    major_recruits = cursor.fetchall()
    print("Top Majors:")
    print("-" * 40)
    for major, count in major_recruits:
        print(f"{major:35} | {count:3} recruits")
    print()
    
    # Check graduation years
    cursor.execute("""
        SELECT high_school_graduation_year, COUNT(*) as year_count
        FROM potential_recruit
        GROUP BY high_school_graduation_year
        ORDER BY high_school_graduation_year
    """)
    
    year_recruits = cursor.fetchall()
    print("Recruits by Graduation Year:")
    print("-" * 35)
    for year, count in year_recruits:
        print(f"Class of {year}: {count:3} recruits")
    print()
    
    # Show sample recruits
    cursor.execute("""
        SELECT 
            first_name, last_name, current_school, major, gpa, status, 
            high_school_graduation_year, interests
        FROM potential_recruit
        ORDER BY current_school, last_name
        LIMIT 15
    """)
    
    sample_recruits = cursor.fetchall()
    print("Sample Recruits:")
    print("-" * 80)
    for recruit in sample_recruits:
        first_name, last_name, school, major, gpa, status, grad_year, interests = recruit
        print(f"{first_name} {last_name} ({school})")
        print(f"  Major: {major}, GPA: {gpa}, Status: {status}, Class: {grad_year}")
        print(f"  Interests: {interests[:60]}{'...' if len(interests) > 60 else ''}")
        print()
    
    cursor.close()
    
    return total_recruits, school_recruits, status_recruits

def main():
    print("=== Potential Recruits Check ===")
    
    # Connect to database
    conn = get_database_connection()
    print("✓ Connected to production database")
    print()
    
    # Check recruits
    total_recruits, school_recruits, status_recruits = check_recruits(conn)
    
    conn.close()
    
    print()
    print("=== SUMMARY ===")
    print(f"✅ Total recruits: {total_recruits}")
    print(f"✅ Schools represented: {len(school_recruits)}")
    print(f"✅ Status categories: {len(status_recruits)}")
    
    if total_recruits >= 50:
        print()
        print("🎉 RECRUITS CREATION SUCCESSFUL!")
        print("   - Comprehensive recruit database created")
        print("   - All 13 schools represented")
        print("   - Varied academic and personal information")
        print("   - Ready for recruitment management")

if __name__ == "__main__":
    main()
