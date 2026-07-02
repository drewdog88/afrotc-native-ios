#!/usr/bin/env python3
"""
Fix PostgreSQL sequences to prevent duplicate key errors
"""

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def fix_postgresql_sequences():
    """Fix all PostgreSQL sequences to start after existing data"""
    database_url = os.getenv('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url, connect_args={'sslmode': 'require'})
    
    with engine.connect() as conn:
        # Fix all sequence values for tables that have data
        tables_with_sequences = [
            ('activity_log', 'activity_log_id_seq'),
            ('cadet', 'cadet_id_seq'), 
            ('contact', 'contact_id_seq'),
            ('external_link', 'external_link_id_seq'),
            ('\"user\"', 'user_id_seq'),  # user is a reserved keyword
            ('recruit', 'recruit_id_seq'),
            ('document', 'document_id_seq'),
            ('event', 'event_id_seq'),
            ('password_history', 'password_history_id_seq')
        ]
        
        for table, sequence in tables_with_sequences:
            try:
                # Get the current max ID
                result = conn.execute(text(f'SELECT COALESCE(MAX(id), 0) + 1 FROM {table}'))
                next_id = result.scalar()
                
                # Reset the sequence
                conn.execute(text(f'ALTER SEQUENCE {sequence} RESTART WITH {next_id}'))
                print(f'✅ Reset {sequence} to start at {next_id}')
                
            except Exception as e:
                print(f'⚠️  Could not fix {sequence}: {e}')
        
        conn.commit()
        print('\n🎉 PostgreSQL sequences fixed!')
        print('The application should now work without duplicate key errors.')

if __name__ == '__main__':
    fix_postgresql_sequences()
