@echo off
title JARVIS AI Assistant
cd /d "%~dp0"
echo Starting JARVIS...
python jarvis.py
if errorlevel 1 (
    echo.
    echo Error: Python nahi mila ya kuch gadbad hui.
    echo Python install karo: https://python.org
    pause
)
