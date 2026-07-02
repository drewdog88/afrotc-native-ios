# AFROTC 695 Backup Scheduler

This system provides automatic nightly backups for the AFROTC 695 Recruitment System database.

## Features

- **Nightly Backups**: Automatic backups at 2:00 AM every day
- **Additional Safety**: Backups every 6 hours during the day
- **Smart Scheduling**: Only creates backups when the server is running
- **Automatic Cleanup**: Removes backups older than 7 days
- **Metadata Tracking**: Each backup includes detailed metadata

## How to Use

### Starting the Backup Scheduler

#### Windows
```bash
# Double-click the file or run from command line:
start_backup_scheduler.bat
```

#### macOS/Linux
```bash
# Make the script executable first:
chmod +x start_backup_scheduler.sh

# Then run:
./start_backup_scheduler.sh
```

#### Manual Start
```bash
# Activate virtual environment first:
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Then run the scheduler:
python scheduled_backup.py
```

### Running a Single Backup

To run a backup immediately (for testing):

```bash
python scheduled_backup.py --now
```

### Stopping the Scheduler

Press `Ctrl+C` to stop the backup scheduler.

## Backup Schedule

- **Primary**: 2:00 AM daily (nightly backup)
- **Secondary**: Every 6 hours during the day (additional safety)
- **Conditional**: Only runs when the Flask server is active

## Backup Storage

- **Location**: `backups/` directory
- **Format**: `afrotc695_backup_YYYYMMDD_HHMMSS.db`
- **Metadata**: `afrotc695_backup_YYYYMMDD_HHMMSS_metadata.json`

## Automatic Cleanup

The system automatically removes backups older than 7 days to prevent disk space issues.

## Monitoring

The scheduler provides real-time feedback:
- Backup start/completion messages
- Server status checks
- Cleanup operations
- Error reporting

## Requirements

- Python 3.7+
- `schedule` package (installed via `pip install schedule==1.2.0`)
- Virtual environment activated
- Flask application running (for backups to be created)

## Troubleshooting

### "Server not running" messages
This is normal when the Flask application is not active. Backups will resume when the server starts.

### Permission errors
Ensure the script has write permissions to the `backups/` directory.

### Database locked errors
This may occur if the Flask application is actively writing to the database. The backup will be retried on the next schedule.

## Integration with Flask App

The backup scheduler works independently of the Flask application but integrates with the existing backup system:

- Uses the same backup directory structure
- Creates compatible backup files
- Includes metadata for the admin interface
- Respects the same file naming conventions 