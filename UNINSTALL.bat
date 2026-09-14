@echo off
title ULTRON AI - UNINSTALL
color 0C
echo.
echo  Removing ULTRON from Windows Startup...
reg delete "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ULTRON-AI" /f >nul 2>&1
del /f .installed >nul 2>&1
echo  Done! ULTRON will no longer auto-start.
echo  Your files are untouched - delete this folder to fully remove.
pause