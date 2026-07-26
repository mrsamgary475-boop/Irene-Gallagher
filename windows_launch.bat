@echo off
setlocal
cd /d "%~dp0"
if not exist ".env" (
  echo .env not found. Copy .env.example to .env and add your Kindroid settings.
  pause
  exit /b 1
)
if not exist ".\.venv\Scripts\python.exe" (
  echo Python venv not found at .\.venv\Scripts\python.exe
  pause
  exit /b 1
)
echo Starting the local Irene Windows app at http://127.0.0.1:8765
start "" http://127.0.0.1:8765
.\.venv\Scripts\python.exe -u local_app.py
endlocal
