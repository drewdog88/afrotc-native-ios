#!/bin/bash

echo "Starting AFROTC 695 Backup Scheduler..."
echo ""
echo "This will run nightly backups at 2:00 AM and every 6 hours during the day."
echo "The scheduler will only create backups when the server is running."
echo ""
echo "Press Ctrl+C to stop the scheduler."
echo ""

# Activate virtual environment
source .venv/bin/activate

# Start the backup scheduler
python scheduled_backup.py 