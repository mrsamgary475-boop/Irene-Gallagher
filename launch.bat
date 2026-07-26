@echo off
REM Launch script for Kindroid Discord Bot (Windows)
SETLOCAL
cd /d "%~dp0"
if not exist .env (
  echo .env not found. Copy .env.example to .env and add your DISCORD_TOKEN and KINDROID_API_KEY.
  echo To create: copy .env.example .env
  echo Then edit .env and add your credentials.
  pause
  exit /b 1
)
if not exist .\.venv\Scripts\python.exe (
  echo Python venv not found at .\.venv\Scripts\python.exe
  echo Create it with: py -m venv .venv
  pause
  exit /b 1
)
echo Starting Irene bot...
.\.venv\Scripts\python.exe -u main.py >> bot.log 2>&1
ENDLOCAL

