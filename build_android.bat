@echo off
REM ============================================================
REM  Build Irene Android APK
REM
REM  This builds a Trusted Web Activity (TWA) wrapper that
REM  packages the Irene PWA into an installable Android app.
REM
REM  Prerequisites (install once):
REM    1. Android Studio or Android SDK + JDK 17
REM    2. Node.js + Bubblewrap CLI:
REM         npm install -g @bubblewrap/cli
REM
REM  The PWA must be served over HTTPS for TWA. For local use,
REM  configure LOCAL_WEB_CERT_FILE / LOCAL_WEB_KEY_FILE in .env
REM  and update the "host" in twa-manifest.json to match.
REM ============================================================
setlocal
cd /d "%~dp0"

where bubblewrap >nul 2>&1
if errorlevel 1 (
  echo Bubblewrap CLI not found. Installing...
  call npm install -g @bubblewrap/cli
  if errorlevel 1 (
    echo ERROR: npm/bubblewrap install failed. Install Node.js first.
    pause
    exit /b 1
  )
)

if not exist "android-project" (
  echo Initializing TWA project from manifest...
  bubblewrap init --manifest twa-manifest.json
  if errorlevel 1 (
    echo ERROR: TWA init failed.
    pause
    exit /b 1
  )
)

echo.
echo Building debug APK...
cd android-project
bubblewrap build
if errorlevel 1 (
  echo ERROR: APK build failed.
  pause
  exit /b 1
)

echo.
if exist "app-release-signed.apk" (
  echo Build successful!
  echo Output: android-project\app-release-signed.apk
  copy /Y app-release-signed.apk ..\IreneApp.apk
  echo Copied to: IreneApp.apk
) else if exist "app-release-unsigned.apk" (
  echo Build successful (unsigned)!
  echo Output: android-project\app-release-unsigned.apk
  copy /Y app-release-unsigned.apk ..\IreneApp-debug.apk
  echo Copied to: IreneApp-debug.apk
) else (
  echo Check android-project\ for the output APK.
)

pause
endlocal
