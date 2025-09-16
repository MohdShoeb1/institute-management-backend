@echo off
echo 🚀 Starting Institute Management System Backend...

REM Check if virtual environment exists
if not exist "venv" (
    echo ❌ Virtual environment not found. Running setup...
    call install-dependencies.bat
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if MongoDB is running (optional check)
echo 🔍 Checking system...

REM Run the application
echo ✅ Starting Flask application...
python app.py

pause
