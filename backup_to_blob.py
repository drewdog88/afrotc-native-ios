#!/usr/bin/env python3
"""
Script to backup Neon PostgreSQL data and save it to Vercel Blob storage
"""

import os
import json
import sys
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
import requests

# Load environment variables
load_dotenv()

def get_neon_connection():
    """Get Neon PostgreSQL connection"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ Error: DATABASE_URL not found in .env file")
        sys.exit(1)
    
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    connect_args = {"sslmode": "require"} if 'postgresql' in database_url else {}
    engine = create_engine(database_url, connect_args=connect_args)
    return engine

def export_table_data(engine, table_name):
    """Export all data from a table"""
    try:
        with engine.connect() as conn:
            # Get all data from the table
            result = conn.execute(text(f'SELECT * FROM "{table_name}"'))
            rows = result.fetchall()
            columns = result.keys()
            
            # Convert to list of dictionaries
            table_data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert datetime objects to ISO format strings
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row_dict[col] = value
                table_data.append(row_dict)
            
            return table_data
    except Exception as e:
        print(f"   ⚠️  Error exporting {table_name}: {e}")
        return []

def create_backup_data(engine):
    """Create complete backup of all tables"""
    print("📊 Exporting data from all tables...")
    
    # Get all table names
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    backup_data = {
        'metadata': {
            'backup_timestamp': datetime.now().isoformat(),
            'database_type': 'postgresql',
            'source': 'neon',
            'total_tables': len(tables),
            'backup_version': '1.0'
        },
        'tables': {}
    }
    
    total_records = 0
    
    for table in tables:
        print(f"   📋 Exporting {table}...")
        table_data = export_table_data(engine, table)
        backup_data['tables'][table] = {
            'record_count': len(table_data),
            'data': table_data
        }
        total_records += len(table_data)
        print(f"      ✅ {len(table_data)} records exported")
    
    backup_data['metadata']['total_records'] = total_records
    print(f"📊 Total records exported: {total_records}")
    
    return backup_data

def upload_to_vercel_blob(data, filename):
    """Upload backup data to Vercel Blob storage"""
    blob_token = os.getenv('BLOB_READ_WRITE_TOKEN')
    if not blob_token:
        print("❌ Error: BLOB_READ_WRITE_TOKEN not found in environment variables")
        return None
    
    print(f"☁️  Uploading {filename} to Vercel Blob...")
    
    # Convert data to JSON string
    json_data = json.dumps(data, indent=2, default=str)
    json_bytes = json_data.encode('utf-8')
    
    # Upload to Vercel Blob using REST API
    url = "https://blob.vercel-storage.com"
    
    headers = {
        'Authorization': f'Bearer {blob_token}',
        'Content-Type': 'application/json'
    }
    
    # Use the PUT method to upload
    upload_url = f"{url}/{filename}"
    
    try:
        response = requests.put(
            upload_url,
            data=json_bytes,
            headers=headers,
            params={
                'addRandomSuffix': 'false'
            }
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"   ✅ Successfully uploaded to: {result.get('url', 'Unknown URL')}")
            return result.get('url')
        else:
            print(f"   ❌ Upload failed with status {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error uploading to blob: {e}")
        return None

def save_local_backup(data, filename):
    """Save backup locally as a fallback"""
    local_path = f"backups/{filename}"
    
    # Create backups directory if it doesn't exist
    os.makedirs("backups", exist_ok=True)
    
    try:
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"   ✅ Local backup saved: {local_path}")
        return local_path
    except Exception as e:
        print(f"   ❌ Error saving local backup: {e}")
        return None

def main():
    """Main backup function"""
    print("🚀 Starting Neon PostgreSQL Backup to Vercel Blob")
    print("=" * 60)
    
    # Test connections
    print("🔍 Testing connections...")
    
    # Test Neon connection
    try:
        engine = get_neon_connection()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"   ✅ Neon PostgreSQL: {version[:50]}...")
    except Exception as e:
        print(f"   ❌ Neon connection failed: {e}")
        return False
    
    # Test Blob token
    blob_token = os.getenv('BLOB_READ_WRITE_TOKEN')
    if blob_token:
        print(f"   ✅ Vercel Blob token: {blob_token[:20]}...")
    else:
        print("   ⚠️  Vercel Blob token not found - will save locally only")
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"neon_backup_{timestamp}.json"
    
    print(f"\n📦 Creating backup: {filename}")
    print("-" * 40)
    
    # Export all data
    backup_data = create_backup_data(engine)
    
    print(f"\n☁️  Uploading to Vercel Blob Storage...")
    print("-" * 40)
    
    # Upload to Vercel Blob
    blob_url = None
    if blob_token:
        blob_url = upload_to_vercel_blob(backup_data, filename)
    
    # Save local backup as fallback
    print(f"\n💾 Saving local backup...")
    print("-" * 40)
    local_path = save_local_backup(backup_data, filename)
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 BACKUP COMPLETED!")
    print("=" * 60)
    print(f"📊 Backup Statistics:")
    print(f"   • Total Tables: {backup_data['metadata']['total_tables']}")
    print(f"   • Total Records: {backup_data['metadata']['total_records']}")
    print(f"   • Backup Size: {len(json.dumps(backup_data, default=str)) / 1024:.1f} KB")
    print(f"   • Created: {backup_data['metadata']['backup_timestamp']}")
    
    print(f"\n📁 Backup Locations:")
    if blob_url:
        print(f"   ☁️  Vercel Blob: {blob_url}")
    if local_path:
        print(f"   💾 Local: {local_path}")
    
    if blob_url or local_path:
        print(f"\n✅ SUCCESS! Your data is now safely backed up!")
        print(f"🔐 You can restore from this backup anytime in the future.")
        return True
    else:
        print(f"\n❌ FAILED! Could not create backup.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
