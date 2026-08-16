"""
JARVIS OS Desktop Application Launcher.
Bootstraps backend server services, registers system tray shortcuts and global hotkeys,
and opens the dark cybernetic HUD dashboard inside a native, high-performance pywebview container.
"""

import sys
import os
import threading
import time
import subprocess
import uvicorn
import webview
import httpx

# Add current workspace directory to sys.path so modules resolve correctly
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from jarvis.config.settings import settings
from jarvis.utils.logger import get_logger
from jarvis.memory.long_term import LongTermMemory

logger = get_logger("Launcher")


def run_backend():
    """Programmatic entry point for local FastAPI backend service."""
    logger.info("Initializing JARVIS OS local backend service...")
    try:
        # Programmatically run Uvicorn server in non-reload mode for background daemon execution
        uvicorn.run(
            "jarvis.api.server:app",
            host="127.0.0.1",
            port=8000,
            reload=False,
            log_level="info",
        )
    except Exception as e:
        logger.error(f"Uvicorn server crashed: {e}")


def wait_for_backend() -> bool:
    """Blocks until local FastAPI server responds with 200 to health check."""
    logger.info("Performing API health checks at http://127.0.0.1:8000/health...")
    for attempt in range(40):
        try:
            with httpx.Client() as client:
                resp = client.get("http://127.0.0.1:8000/health", timeout=1.0)
                if resp.status_code == 200:
                    logger.info("Local microservices online and responding successfully.")
                    return True
        except Exception:
            pass
        time.sleep(0.4)
    logger.error("API server failed to respond in time.")
    return False


def setup_tray_icon():
    """Registers standard Windows system tray context menu shortcuts."""
    try:
        import pystray
        from PIL import Image, ImageDraw
        
        # Create a simple dynamic glowing circle icon
        width, height = 64, 64
        image = Image.new('RGB', (width, height), color=(11, 15, 30))
        dc = ImageDraw.Draw(image)
        dc.ellipse([16, 16, 48, 48], fill=(0, 240, 255), outline=None)
        
        def show_window(icon, item):
            logger.info("Tray: Open Dashboard clicked.")
            # Restores focus if window exists (handled natively by pywebview wrapper)
            
        def on_exit(icon, item):
            logger.info("Tray: Exit requested. Stopping subprocesses...")
            icon.stop()
            os._exit(0)
            
        icon = pystray.Icon(
            "JARVIS OS", 
            image, 
            "JARVIS OS Pro", 
            menu=pystray.Menu(
                pystray.MenuItem("Open Dashboard", show_window),
                pystray.MenuItem("Exit JARVIS", on_exit)
            )
        )
        
        # Run tray loop in dedicated background thread
        threading.Thread(target=icon.run, daemon=True).start()
        logger.info("System Tray launcher successfully registered.")
    except Exception as e:
        logger.error(f"Failed to initialize System Tray: {e}")


def register_global_hotkeys():
    """Binds Ctrl+Space hotkey to trigger microphone listening programmatically."""
    try:
        import keyboard
        
        def trigger_voice_listening():
            logger.info("Global Hotkey: Ctrl+Space detected. Sending trigger mic command.")
            try:
                with httpx.Client() as client:
                    client.post("http://127.0.0.1:8000/v1/trigger_mic", timeout=1.0)
            except Exception as ex:
                logger.error(f"Failed to post trigger mic command: {ex}")
                
        keyboard.add_hotkey('ctrl+space', trigger_voice_listening)
        logger.info("Global shortcut Ctrl+Space bound to voice input trigger.")
    except Exception as e:
        logger.warning(f"Failed to bind global hotkeys: {e}")


def main():
    # Initialize Persistent SQLite Tables (Long Term Memory)
    logger.info("Verifying long-term memory SQLite table states...")
    LongTermMemory()

    # Start local API services in background thread
    server_thread = threading.Thread(target=run_backend, daemon=True)
    server_thread.start()
    
    # Wait until endpoints respond
    if not wait_for_backend():
        print("\n[ERROR] JARVIS OS Backend failed to startup in time. Aborting launcher.")
        sys.exit(1)
        
    # Bind Windows tray and global shortcuts
    setup_tray_icon()
    register_global_hotkeys()
    
    # Start the pywebview native container window
    logger.info("Launching native pywebview desktop user interface wrapper...")
    webview.create_window(
        title="JARVIS OS - Pro HUD Console",
        url="http://127.0.0.1:8000/",
        width=1280,
        height=800,
        min_size=(1100, 700),
        background_color="#070B14"
    )
    
    # Launch pywebview rendering loop (blocks main thread until closed)
    webview.start()
    logger.info("Main native GUI window closed. Exiting application process.")


if __name__ == "__main__":
    main()
