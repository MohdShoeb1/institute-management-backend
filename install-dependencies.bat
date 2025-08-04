@echo off
echo 🚀 Installing Python Dependencies for Institute Management System...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python found

REM Create virtual environment
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo 📥 Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📦 Installing dependencies...
pip install Flask==2.3.3
pip install Flask-CORS==4.0.0
pip install pymongo==4.6.0
pip install PyJWT==2.8.0
pip install bcrypt==4.1.2
pip install python-dotenv==1.0.0

echo ✅ All dependencies installed successfully!
echo.
echo 🚀 To run the server:
echo 1. Run: venv\Scripts\activate.bat
echo 2. Run: python app.py
echo.
pause
