@echo off
REM Wipes HR data and reloads the synthetic NexGen Holdings demo dataset.
cd /d "%~dp0..\backend"
call venv\Scripts\activate.bat
python manage.py seed_demo --reset
pause
