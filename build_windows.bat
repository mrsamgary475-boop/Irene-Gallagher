@echo off
REM ============================================================
REM  Build IreneApp.exe (Windows desktop version)
REM  Run this on a Windows machine with Python + venv installed.
REM ============================================================
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  py -m venv .venv
)

echo Installing dependencies...
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pyinstaller

echo.
echo Building IreneApp.exe with PyInstaller...
.\.venv\Scripts\python.exe -m PyInstaller Irene.spec --noconfirm --clean

echo.
if exist "dist\IreneApp\IreneApp.exe" (
  echo Build successful!
  echo Output: dist\IreneApp\IreneApp.exe
  echo.
  echo To run: dist\IreneApp\IreneApp.exe
  echo Make sure .env is in the dist\IreneApp\ folder.
) else (
  echo Build FAILED - check output above.
)

pause
endlocal
