"""
JARVIS OS - Master Launcher & Desktop Entry Point.
Launches the FastAPI backend in background and the Desktop GUI on screen.
One command: python launch.py
"""

import sys
import os
import time
import subprocess
import threading


def start_backend():
    """Starts FastAPI Uvicorn backend microservice in background (for API only, no browser needed)."""
    subprocess.run([sys.executable, "-m", "jarvis.main"])


def main():
    print("================================================================")
    print("                 STARTING JARVIS OS DESKTOP                     ")
    print("       Enterprise AI Desktop Operating Layer v1.0.0             ")
    print("================================================================")

    # Launch FastAPI backend silently in background thread
    server_thread = threading.Thread(target=start_backend, daemon=True)
    server_thread.start()
    time.sleep(2)  # Give backend time to start

    # Launch Desktop GUI (this blocks until window is closed)
    from jarvis.ui.app import launch_gui
    launch_gui()


if __name__ == "__main__":
    main()
