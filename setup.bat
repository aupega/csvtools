@echo off
REM Setup script for Windows
REM Installs Python (if not present), pip, and all dependencies for csv_compare_flask

REM Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python not found. Please install Python 3.8+ from https://www.python.org/downloads/
    echo Opening Python download page...
    start https://www.python.org/downloads/
    echo After installation, please re-run this script.
    exit /b 1
)

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dependencies
python -m pip install -r requirements.txt

echo Setup complete. You can now run: flask run
