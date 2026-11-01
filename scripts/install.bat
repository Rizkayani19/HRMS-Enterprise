@echo off
REM ============================================================
REM  Enterprise HRMS (demo) - one-time setup on Windows
REM  Needs Python 3.10+ on PATH. Uses SQLite unless backend\.env
REM  says otherwise, so no database server is needed for the demo.
REM ============================================================
setlocal
cd /d "%~dp0..\backend"

where python >nul 2>nul || (echo Python was not found on PATH. Install Python 3.10+ and try again. & pause & exit /b 1)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv || (echo Could not create the virtual environment. & pause & exit /b 1)
)
call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt || (echo Dependency install failed. & pause & exit /b 1)

if not exist .env (
    copy .env.example .env >nul
    echo Created backend\.env from the example - SQLite, development mode.
)

echo Preparing database...
python manage.py migrate || (pause & exit /b 1)
python manage.py seed_demo
python manage.py collectstatic --noinput >nul

echo.
echo Setup complete. Run scripts\start_hrms.bat to launch.
echo Demo sign-in: admin / admin123
pause
