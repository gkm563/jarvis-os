"""
Permission & Role-Based Access Control (RBAC) Manager.
Enforces scope validation and access limits for domain agents.
"""

from typing import Dict, List, Set
from jarvis.core.models import AgentAction, PermissionScope
from jarvis.core.exceptions import SecurityError
from jarvis.utils.logger import get_logger

logger = get_logger("PermissionManager")


class PermissionManager:
    """
    Evaluates and enforces permission rules for agent execution.
    """

    def __init__(self):
        # Default granted permissions per agent
        self._granted_permissions: Dict[str, Set[str]] = {
            "desktop_agent": {"launch_app", "focus_window", "system_state", "snap_window", "close_app"},
            "browser_agent": {"navigate", "fill_form", "download_file", "manage_tabs", "screenshot"},
            "file_agent": {"read_file", "write_file", "delete_file", "organize_folder", "duplicate_scan"},
            "coding_agent": {"read_code", "edit_code", "run_test", "git_commit", "git_push"},
            "vision_agent": {"capture_screen", "ocr", "classify_ui"},
            "voice_agent": {"stt", "tts", "wake_word"},
            "security_agent": {"vault_access", "permission_check"},
        }

    def check_permission(self, agent_name: str, action_type: str) -> bool:
        """
        Validates whether an agent has permission to perform an action type.

        Args:
            agent_name (str): Agent identifier.
            action_type (str): Requested action.

        Returns:
            bool: True if permitted.
        """
        agent_perms = self._granted_permissions.get(agent_name, set())
        if action_type in agent_perms:
            return True

        logger.warning(
            f"Permission DENIED: Agent '{agent_name}' attempted unauthorized action '{action_type}'",
            extra={"audit": True},
        )
        return False

    def validate_action_scope(self, agent_name: str, action: AgentAction) -> None:
        """
        Raises SecurityError if requested action exceeds permitted bounds.
        """
        if not self.check_permission(agent_name, action.action_type):
            raise SecurityError(
                f"Agent '{agent_name}' lacks required permission for action '{action.action_type}'"
            )
