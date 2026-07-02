@echo off
echo Starting AFROTC 695 Neon Backup Scheduler...
echo.
echo This will run nightly backups at 2:00 AM and every 6 hours during the day.
echo Backup retention: 30 days
echo Storage: Vercel Blob
echo.
echo Press Ctrl+C to stop the scheduler.
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start the backup scheduler
python neon_backup_scheduler.py

pause
