#!/usr/bin/env python3

from app_local import db, app, User, PotentialRecruit, Cadet, UniversityContact, RecruitmentEvent, RecruitmentDocument, ExternalLink, ActivityLog
import os

def check_database_tables():
    """Check what tables exist in the database and what tables are defined in models"""
    
    with app.app_context():
        print("=== Database Connection Info ===")
        print(f"Database URL: {os.getenv('DATABASE_URL', 'Not found in env')}")
        print(f"Engine: {db.engine}")
        
        print("\n=== Tables defined in SQLAlchemy models ===")
        for table_name in db.metadata.tables.keys():
            print(f"  - {table_name}")
        
        print("\n=== Tables that exist in the database ===")
        # Get all table names from the database
        result = db.session.execute(db.text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        
        db_tables = [row[0] for row in result.fetchall()]
        for table_name in db_tables:
            print(f"  - {table_name}")
        
        print(f"\n=== Summary ===")
        print(f"Tables in models: {len(db.metadata.tables)}")
        print(f"Tables in database: {len(db_tables)}")
        
        # Check for missing tables
        model_tables = set(db.metadata.tables.keys())
        db_table_set = set(db_tables)
        
        missing_in_db = model_tables - db_table_set
        if missing_in_db:
            print(f"\n❌ Tables missing from database: {missing_in_db}")
        else:
            print("\n✅ All model tables exist in database")
        
        extra_in_db = db_table_set - model_tables
        if extra_in_db:
            print(f"\n⚠️  Extra tables in database: {extra_in_db}")
        
        # Try to query potential_recruit table directly
        print("\n=== Testing potential_recruit table access ===")
        try:
            # Try raw SQL first
            result = db.session.execute(db.text("SELECT COUNT(*) FROM potential_recruit"))
            count = result.scalar()
            print(f"✅ Raw SQL query successful: {count} records")
            
            # Try SQLAlchemy ORM
            count_orm = PotentialRecruit.query.count()
            print(f"✅ SQLAlchemy ORM query successful: {count_orm} records")
            
        except Exception as e:
            print(f"❌ Error querying potential_recruit table: {e}")
            print(f"Error type: {type(e)}")
            
            # Check if it's a schema issue
            try:
                result = db.session.execute(db.text("""
                    SELECT schemaname, tablename 
                    FROM pg_tables 
                    WHERE tablename = 'potential_recruit'
                """))
                schemas = result.fetchall()
                print(f"Table found in schemas: {schemas}")
            except Exception as schema_e:
                print(f"Error checking schemas: {schema_e}")

if __name__ == "__main__":
    check_database_tables()
