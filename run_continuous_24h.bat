@echo off
title AI Social Media Agent - 24/7 Background Runner
cd /d "%~dp0"

echo ======================================================================
echo    AI SOCIAL MEDIA AGENT - 24/7 BACKGROUND SYSTEM ACTIVE
echo    - Multi-Brand: Phono Print Tegal & Cultivare Collective
echo    - Dashboard: http://127.0.0.1:5000
echo ======================================================================

set PYTHON_EXE=C:\Users\LENOVOII\AppData\Local\Python\pythoncore-3.14-64\python.exe

if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

start "" /B "%PYTHON_EXE%" admin_app.py

echo.
echo [*] Admin Dashboard Server running on http://127.0.0.1:5000
echo [*] To run on Windows Startup, copy a shortcut of this file to shell:startup
echo ======================================================================
pause
