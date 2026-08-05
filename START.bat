@echo off
title JARVIS AI Assistant
cd /d "%~dp0"
echo.
echo  ========================================
echo    JARVIS AI - Starting...
echo    Boliye ya type kariye
echo  ========================================
echo.
python jarvis.py
if errorlevel 1 (
    echo.
    echo  ERROR: Python nahi mila!
    echo  Install karo: https://python.org
    pause
)
