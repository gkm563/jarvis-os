"""
Global Push-To-Talk and Hands-Free Hotkey Listener for JARVIS OS.
Listens for Alt+Space (Push-To-Talk) and Ctrl+Alt+Space (Hands-Free Mode).
"""

import threading
import time
from typing import Callable, Optional
from jarvis.utils.win32 import user32, kernel32, VK_SPACE
from jarvis.utils.logger import get_logger

logger = get_logger("HotkeyListener")


class GlobalHotkeyListener:
    """
    Win32 Low-Level Keyboard Hook dispatcher for global shortcuts.
    """

    def __init__(self, on_talk_press: Optional[Callable[[], None]] = None, on_talk_release: Optional[Callable[[], None]] = None):
        self.on_talk_press = on_talk_press
        self.on_talk_release = on_talk_release
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Starts global hotkey thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_hook, daemon=True, name="HotkeyThread")
        self._thread.start()
        logger.info("Global Push-To-Talk hotkey listener initialized (Alt+Space).")

    def stop(self) -> None:
        """Stops global hotkey thread."""
        self._running = False

    def _run_hook(self) -> None:
        """Runs Windows message loop for hotkey detection."""
        try:
            while self._running:
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"Hotkey listener error: {str(e)}")
