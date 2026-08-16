@echo off
title JARVIS OS Launcher
cd /d "%~dp0"
echo.
echo  ================================================================
echo                      STARTING JARVIS OS                         
echo         Cybernetic AI Desktop Operating Layer v3.1.1            
echo  ================================================================
echo.

python -c "import sounddevice, edge_tts, webview, pystray, keyboard, psutil" 2>nul || (
    echo  Installing required voice ^& system dependencies...
    python -m pip install -r requirements.txt -q
    python -m pip install -r requirements-voice.txt -q
    echo.
)

python launch.py
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Failed to launch JARVIS OS!
    echo  Please ensure Python 3.10+ is installed and check logs/jarvis.log.
    pause
)
