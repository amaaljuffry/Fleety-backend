@echo off
REM Fleety Backend Startup Script for Windows

echo.
echo ====================================
echo Fleety Backend - Startup Script
echo ====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if virtual environment exists, if not create it
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install -q -r requirements.txt

REM Check if .env file exists
if not exist ".env" (
    echo Creating .env file from .env.example...
    copy .env.example .env
)

echo.
echo ====================================
echo Starting Fleety Backend
echo ====================================
echo API will be available at: http://localhost:8000
echo API Docs at: http://localhost:8000/docs
echo.
echo Make sure MongoDB is running on localhost:27017
echo Or update MONGODB_URL in .env
echo.

REM Start the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
