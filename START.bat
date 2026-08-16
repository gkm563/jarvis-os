@echo off
title JARVIS AI Assistant
cd /d "%~dp0"
echo.
echo  ========================================
echo    JARVIS AI - Starting...
echo    English Voice Assistant
echo  ========================================
echo.
echo  Installing voice engine (first time only)...
python -m pip install -r requirements-voice.txt -q 2>nul
echo.
python jarvis.py
if errorlevel 1 (
    echo.
    echo  ERROR: Python not found!
    echo  Install from: https://python.org
    pause
)
