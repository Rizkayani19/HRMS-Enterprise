@echo off
REM Writes a timestamped database backup to the backups\ folder.
cd /d "%~dp0..\backend"
call venv\Scripts\activate.bat
python manage.py backup_db
pause
