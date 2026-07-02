#!/bin/bash

echo "Starting AFROTC 695 Neon Backup Scheduler..."
echo ""
echo "This will run nightly backups at 2:00 AM and every 6 hours during the day."
echo "Backup retention: 30 days"
echo "Storage: Vercel Blob"
echo ""
echo "Press Ctrl+C to stop the scheduler."
echo ""

# Activate virtual environment
source .venv/bin/activate

# Start the backup scheduler
python neon_backup_scheduler.py
