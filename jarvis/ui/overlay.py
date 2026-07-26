"""
JARVIS OS HUD Visualizer & Overlay Widget.
"""

from jarvis.utils.logger import get_logger

logger = get_logger("UI_Overlay")


class HUDOverlay:
    def show_notification(self, title: str, message: str):
        logger.info(f"[HUD Notification] {title}: {message}")

    def request_human_confirmation(self, action_description: str, token: str):
        logger.warning(f"[HUD SECURITY GATE] Sensitive action requested: '{action_description}'. Confirmation Token: '{token}'")
