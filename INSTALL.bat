@echo off
title ULTRON AI - INSTALLER
color 0B
echo.
echo  ========================================
echo   ULTRON AI - WINDOWS INSTALLER
echo  ========================================
echo.

cd /d "%~dp0"
set ULTRON_PATH=%~dp0

echo  [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found!
    echo  Install Python 3.10+ from https://python.org
    echo  Check 'Add Python to PATH' during install!
    pause
    exit /b 1
)
echo  [1/4] Python OK!

echo  [2/4] Installing dependencies...
pip install -r requirements.txt
echo  [2/4] Done!

echo  [3/4] Setting up .env file...
if not exist ".env" (
    copy .env.example .env >nul
    echo  Opening .env - add your API keys then save and close...
    notepad .env
) else (
    echo  [3/4] .env already exists.
)

echo  [4/4] Adding ULTRON to Windows Startup...
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ULTRON-AI" /t REG_SZ /d "cmd /c start /B /MIN pythonw \"%ULTRON_PATH%run_ultron.py\"" /f >nul
echo  [4/4] ULTRON will now start automatically on Windows boot!

echo.
echo  ========================================
echo   INSTALLATION COMPLETE!
echo  ========================================
echo.
echo  - Double-click ULTRON.bat to start manually anytime
echo  - Or restart your PC - ULTRON starts automatically!
echo  - Say your wake word to activate
echo  - HUD appears in the bottom-right corner of your screen
echo.
echo  Press any key to launch ULTRON now...
pause >nul

start "" /B pythonw run_ultron.py
echo  ULTRON is running!
timeout /t 3 >nul