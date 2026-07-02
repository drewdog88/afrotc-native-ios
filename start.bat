@echo off
echo AFROTC 695 Recruitment Management System
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install requirements if needed
echo Checking dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements
    pause
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo Creating .env file...
    copy env.example .env
)

REM Ensure database is properly set up
echo Checking database schema...
python -c "
import sqlite3
import os
try:
    conn = sqlite3.connect('instance/afrotc695.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(cadet)')
    columns = [col[1] for col in cursor.fetchall()]
    if 'status' not in columns:
        print('Database needs migration. Please run: python -c \"from app import app, db; app.app_context().push(); db.create_all()\"')
    else:
        print('Database schema is correct.')
    conn.close()
except:
    print('Database will be created on first run.')
"

REM Start the application
echo.
echo Starting AFROTC 695 Recruitment Management System...
echo Access the application at: http://localhost:5000
echo Default login: admin / admin123
echo Press Ctrl+C to stop the server
echo.
python run.py

pause 