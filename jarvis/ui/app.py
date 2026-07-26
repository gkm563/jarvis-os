"""
JARVIS OS Desktop Interface Launcher.
Renders HUD overlay and active task visualizer.
"""

import sys
from jarvis.utils.logger import get_logger

logger = get_logger("DesktopUI")


class DesktopApp:
    """
    Desktop Interface Application Manager.
    """

    def launch(self):
        """Launches the JARVIS OS desktop GUI overlay."""
        logger.info("Launching JARVIS OS Desktop GUI overlay...")
        print("==================================================")
        print("         JARVIS OS - DESKTOP AGENT HUD           ")
        print("==================================================")
        print(" status: ACTIVE | voice: LISTENING | mode: LOCAL")
        print(" Press 'Hey Jarvis' or type instruction below.")
        print("==================================================")


def run_ui():
    app = DesktopApp()
    app.launch()


if __name__ == "__main__":
    run_ui()
