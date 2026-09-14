@echo off
title ULTRON AI
color 0B
echo.
echo  ██╗   ██╗██╗  ████████╗██████╗  ██████╗ ███╗   ██╗
echo  ██║   ██║██║  ╚══██╔══╝██╔══██╗██╔═══██╗████╗  ██║
echo  ██║   ██║██║     ██║   ██████╔╝██║   ██║██╔██╗ ██║
echo  ██║   ██║██║     ██║   ██╔══██╗██║   ██║██║╚██╗██║
echo  ╚██████╔╝███████╗██║   ██║  ██║╚██████╔╝██║ ╚████║
echo   ╚═════╝ ╚══════╝╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
echo.
echo  [ AI SYSTEMS INITIALIZING... ]
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found! Install Python 3.10+ from python.org
    pause
    exit /b 1
)

if not exist ".env" (
    echo  [SETUP] Creating .env from template...
    copy .env.example .env >nul
    echo  [SETUP] Please fill in your API keys in .env file!
    notepad .env
    echo  Press any key to continue after saving .env...
    pause >nul
)

if not exist ".installed" (
    echo  [SETUP] Installing dependencies...
    pip install -r requirements.txt -q
    echo installed > .installed
)

echo  [ LAUNCHING ULTRON AI... ]
start "" /B pythonw run_ultron.py
echo  [ ULTRON IS NOW RUNNING - HUD will appear on screen ]
timeout /t 3 >nul