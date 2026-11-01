@echo off
REM Starts Enterprise HRMS on http://127.0.0.1:8888 in the background and opens it.
cd /d "%~dp0"
wscript.exe "%~dp0start_hrms_silent.vbs"
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:8888/
