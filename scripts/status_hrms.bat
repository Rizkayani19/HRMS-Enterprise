@echo off
netstat -ano | findstr /r /c:":8888 .*LISTENING" >nul && (echo HRMS is RUNNING on http://127.0.0.1:8888/) || (echo HRMS is STOPPED.)
pause
