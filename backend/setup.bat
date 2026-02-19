@echo off
REM Setup script for Gmail AI Expense Tracker Backend (Windows)

echo Setting up Gmail AI Expense Tracker Backend...

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file with your configuration
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Activate the virtual environment: venv\Scripts\activate
echo 2. Edit .env file with your configuration
echo 3. Run database migrations: alembic upgrade head
echo 4. Start the server: python main.py

pause
