#!/usr/bin/env python3
"""
Scheduled Backup Script for AFROTC 695 Recruitment System (MySQL Version)
This script runs nightly backups when the server is running.
"""

import os
import sys
import time
import schedule
import threading
from datetime import datetime
import subprocess
import shutil
import json

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Database backup configuration
BACKUP_DIR = 'backups'
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

def get_database_config():
    """Get database configuration from environment or .env file"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        database_url = os.getenv('DATABASE_URL', '')
        if not database_url:
            # Fallback to default values
            return {
                'username': 'cascznjx_afrotcdbadmin',
                'password': 'E3@8SXMxNPHG',
                'host': 'localhost',
                'port': '3306',
                'database': 'cascznjx_afrotc_recruit'
            }
        
        # Parse MySQL connection string
        # Format: mysql+pymysql://username:password@host:port/database
        if database_url.startswith('mysql+pymysql://'):
            database_url = database_url.replace('mysql+pymysql://', '')
        
        if '@' in database_url:
            auth_part, rest = database_url.split('@', 1)
            if ':' in auth_part:
                username, password = auth_part.split(':', 1)
                password = password.replace('%40', '@')  # URL decode @ symbol
            else:
                username = auth_part
                password = ''
            
            if '/' in rest:
                host_port, database = rest.split('/', 1)
                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                else:
                    host = host_port
                    port = '3306'
            else:
                host = rest
                port = '3306'
                database = ''
        else:
            # Fallback parsing
            username = 'cascznjx_afrotcdbadmin'
            password = 'E3@8SXMxNPHG'
            host = 'localhost'
            port = '3306'
            database = 'cascznjx_afrotc_recruit'
        
        return {
            'username': username,
            'password': password,
            'host': host,
            'port': port,
            'database': database
        }
    except Exception as e:
        print(f"Error getting database config: {e}")
        # Return default values
        return {
            'username': 'cascznjx_afrotcdbadmin',
            'password': 'E3@8SXMxNPHG',
            'host': 'localhost',
            'port': '3306',
            'database': 'cascznjx_afrotc_recruit'
        }

def backup_database_standalone(description="Nightly automatic backup"):
    """Create a MySQL database backup with timestamp and description (standalone version)"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"afrotc695_backup_{timestamp}.sql"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        
        # Get database configuration
        db_config = get_database_config()
        
        # Build mysqldump command
        # Define full path to mysqldump
        mysql_bin_path = r"C:\Program Files\MySQL\MySQL Server 8.0\bin"
        mysqldump_path = os.path.join(mysql_bin_path, "mysqldump.exe")
        
        cmd = [
            mysqldump_path,
            f'--host={db_config["host"]}',
            f'--port={db_config["port"]}',
            f'--user={db_config["username"]}',
            '--single-transaction',
            '--routines',
            '--triggers',
            '--add-drop-database',
            '--create-options',
            db_config['database']
        ]
        
        # Set password via environment variable for security
        env = os.environ.copy()
        env['MYSQL_PWD'] = db_config['password']
        
        # Execute mysqldump
        with open(backup_path, 'w') as backup_file:
            result = subprocess.run(
                cmd,
                stdout=backup_file,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
        
        if result.returncode != 0:
            raise Exception(f"mysqldump failed: {result.stderr}")
        
        # Create backup metadata
        metadata = {
            'timestamp': timestamp,
            'description': description,
            'filename': backup_filename,
            'size': os.path.getsize(backup_path),
            'user': 'Scheduled Backup System',
            'database': db_config['database'],
            'host': db_config['host']
        }
        
        # Save metadata to a JSON file
        metadata_file = backup_path.replace('.sql', '_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Database backup created: {backup_filename}")
        return backup_filename, backup_path
        
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None, None

def check_server_running():
    """Check if the MySQL server is running by trying to connect to the database"""
    try:
        db_config = get_database_config()
        
        # Try to connect using mysql command
        cmd = [
            'mysql',
            f'--host={db_config["host"]}',
            f'--port={db_config["port"]}',
            f'--user={db_config["username"]}',
            '--execute=SELECT 1;',
            db_config['database']
        ]
        
        env = os.environ.copy()
        env['MYSQL_PWD'] = db_config['password']
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        
        return result.returncode == 0
    except Exception as e:
        print(f"Server not running or database not accessible: {e}")
        return False

def perform_nightly_backup():
    """Perform the nightly backup if the server is running"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] Starting nightly backup...")
    
    if not check_server_running():
        print(f"[{timestamp}] Server not running, skipping backup")
        return
    
    try:
        # Create backup with description
        backup_filename, backup_path = backup_database_standalone("Nightly automatic backup")
        
        if backup_filename:
            print(f"[{timestamp}] Nightly backup completed successfully: {backup_filename}")
            
            # Clean up old backups (keep last 7 days)
            cleanup_old_backups()
        else:
            print(f"[{timestamp}] Nightly backup failed")
            
    except Exception as e:
        print(f"[{timestamp}] Error during nightly backup: {e}")

def cleanup_old_backups():
    """Clean up backups older than 7 days"""
    try:
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for filename in os.listdir(BACKUP_DIR):
            if filename.endswith('.sql'):
                backup_path = os.path.join(BACKUP_DIR, filename)
                file_modified = datetime.fromtimestamp(os.path.getmtime(backup_path))
                
                if file_modified < cutoff_date:
                    # Remove the backup file and its metadata
                    os.remove(backup_path)
                    metadata_file = backup_path.replace('.sql', '_metadata.json')
                    if os.path.exists(metadata_file):
                        os.remove(metadata_file)
                    print(f"Cleaned up old backup: {filename}")
                    
    except Exception as e:
        print(f"Error during backup cleanup: {e}")

def run_backup_scheduler():
    """Run the backup scheduler"""
    print("Starting AFROTC 695 Backup Scheduler...")
    print("Nightly backups will run at 2:00 AM")
    print("Additional backups will run every 6 hours during the day")
    print("Press Ctrl+C to stop the scheduler")
    
    # Schedule nightly backup at 2:00 AM
    schedule.every().day.at("02:00").do(perform_nightly_backup)
    
    # Also run a backup every 6 hours during the day for additional safety
    schedule.every(6).hours.do(perform_nightly_backup)
    
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

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # Run a single backup immediately
        run_single_backup()
    else:
        # Run the scheduled backup system
        run_backup_scheduler() 