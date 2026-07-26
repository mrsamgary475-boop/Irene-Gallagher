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
set "LOCAL_WEB_HOST=0.0.0.0"
set "LOCAL_WEB_PORT=8765"
echo.
echo Irene is available to Android devices on the same Wi-Fi.
echo On the phone, open one of these addresses:
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
  for /f "tokens=* delims= " %%B in ("%%A") do echo http://%%B:8765
)
echo.
echo Camera and microphone require HTTPS in Android Chrome.
echo See the Android section in README.md for secure setup.
echo.
.\.venv\Scripts\python.exe -u local_app.py
endlocal
