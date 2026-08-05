"""
JARVIS OS - Master Launcher & Desktop Entry Point.
Launches the FastAPI backend microservice, local Web Dashboard (http://localhost:8000), global hotkey listener (Alt+Space), and Desktop HUD.
"""

import sys
import os
import time
import subprocess
import threading
from jarvis.utils.hotkey import GlobalHotkeyListener

def start_backend():
    """Starts FastAPI Uvicorn backend microservice."""
    subprocess.run([sys.executable, "-m", "jarvis.main"])

def main():
    print("================================================================")
    print("                 STARTING JARVIS OS DESKTOP                     ")
    print("       Enterprise AI Desktop Operating Layer v1.0.0             ")
    print("================================================================")
    print(" [1] Microservice API: http://localhost:8000")
    print(" [2] Web Dashboard:    http://localhost:8000/dashboard")
    print(" [3] Global Push-To-Talk Hotkey: Alt+Space")
    print("================================================================")

    # Initialize Global Hotkey Listener
    hotkey = GlobalHotkeyListener()
    hotkey.start()

    # Launch FastAPI Server in background thread
    server_thread = threading.Thread(target=start_backend, daemon=True)
    server_thread.start()
    time.sleep(1.5)

    # Launch Desktop Interface GUI
    try:
        from jarvis.ui.app import launch_gui
        launch_gui()
    except Exception as e:
        print(f"GUI launch info: {str(e)}. Web Dashboard running on http://localhost:8000")

if __name__ == "__main__":
    main()
