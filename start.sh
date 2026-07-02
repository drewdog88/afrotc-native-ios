#!/bin/bash

echo "AFROTC 695 Recruitment Management System"
echo "========================================"
echo

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Failed to activate virtual environment"
    exit 1
fi

# Install requirements if needed
echo "Checking dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install requirements"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp env.example .env
fi

# Start the application
echo
echo "Starting AFROTC 695 Recruitment Management System..."
echo "Access the application at: http://localhost:5000"
echo "Default login: admin / admin123"
echo "Press Ctrl+C to stop the server"
echo
python run.py 