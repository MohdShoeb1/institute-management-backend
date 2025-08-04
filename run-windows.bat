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

REM Set environment variables
if exist ".env" (
    echo 🔐 Loading environment variables...
    for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b
)

REM Run the application
echo ✅ Starting Flask application...
echo.
echo 👤 Available Users:
echo    - Shoeb (Password: Shoeb5550)
echo    - admin (Password: admin123)
echo    - teacher (Password: teacher123)
echo.
python app.py

pause
