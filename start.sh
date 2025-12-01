#!/bin/bash
# Fleety Backend Startup Script for macOS/Linux

echo ""
echo "===================================="
echo "Fleety Backend - Startup Script"
echo "===================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ from https://www.python.org/"
    exit 1
fi

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

echo ""
echo "===================================="
echo "Starting Fleety Backend"
echo "===================================="
echo "API will be available at: http://localhost:8000"
echo "API Docs at: http://localhost:8000/docs"
echo ""
echo "Make sure MongoDB is running"
echo "Or update MONGODB_URL in .env"
echo ""

# Start the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
