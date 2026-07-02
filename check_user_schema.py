#!/usr/bin/env python3
"""
Check the actual User table schema in PostgreSQL
"""

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv('DATABASE_URL')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

engine = create_engine(database_url, connect_args={'sslmode': 'require'})

with engine.connect() as conn:
    result = conn.execute(text("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'user' ORDER BY ordinal_position"))
    print('PostgreSQL User table columns:')
    for row in result:
        print(f'  {row[0]} - {row[1]} - nullable: {row[2]}')
