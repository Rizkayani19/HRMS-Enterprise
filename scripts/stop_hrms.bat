@echo off
REM Stops whatever is listening on port 8888 (the HRMS server).
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":8888 .*LISTENING"') do (
    taskkill /PID %%p /F >nul 2>nul && echo Stopped HRMS server, PID %%p.
)
