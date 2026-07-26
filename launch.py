"""
JARVIS OS - Master Launcher & Desktop App Entry Point.
Launches the FastAPI backend microservice in a background process
and brings up the CustomTkinter Desktop Command Center HUD.
"""

import sys
import os
import time
import subprocess
import threading

def start_backend():
    """Starts FastAPI Uvicorn backend microservice."""
    subprocess.run([sys.executable, "-m", "jarvis.main"])

def main():
    print("================================================================")
    print("                 STARTING JARVIS OS DESKTOP                     ")
    print("       Enterprise AI Desktop Operating Layer v1.0.0             ")
    print("================================================================")

    # Launch FastAPI Server in background thread
    server_thread = threading.Thread(target=start_backend, daemon=True)
    server_thread.start()
    time.sleep(1.5)

    # Launch Desktop Interface GUI
    from jarvis.ui.app import launch_gui
    launch_gui()

if __name__ == "__main__":
    main()
