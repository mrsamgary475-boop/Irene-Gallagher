@echo off
REM Launch Irene with Kindroid-style video avatar interface

cd /d "%~dp0"

REM Start Python app
python local_app.py

REM Open browser to video avatar page
timeout /t 3 /nobreak
start http://localhost:8765/video

pause
