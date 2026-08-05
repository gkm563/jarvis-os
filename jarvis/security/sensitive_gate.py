"""
Human-in-the-Loop Sensitive Action Gate for JARVIS OS.
Requires explicit user confirmation before executing dangerous or irreversible operations.
"""

import uuid
from typing import Dict, Optional, Set
from jarvis.core.models import AgentAction, Step
from jarvis.core.exceptions import ActionDeniedError
from jarvis.config.settings import settings
from jarvis.utils.logger import get_logger

logger = get_logger("SensitiveActionGate")


class SensitiveActionGate:
    """
    Manages human authorization tokens for sensitive actions.
    """

    SENSITIVE_ACTION_CLASSES: Set[str] = {
        "banking_transaction",
        "payment",
        "password_change",
        "credential_update",
        "mass_file_deletion",
        "system_shutdown",
        "system_restart",
        "git_push_production",
    }

    def __init__(self):
        self._pending_tokens: Dict[str, Step] = {}
        self._approved_tokens: Set[str] = set()

    def is_sensitive(self, action: AgentAction) -> bool:
        """
        Determines if an agent action is classified as sensitive.

        Args:
            action (AgentAction): Action instance.

        Returns:
            bool: True if human confirmation is required.
        """
        if action.is_sensitive:
            return True

        if action.action_class in self.SENSITIVE_ACTION_CLASSES:
            return True

        # Check for bulk deletion threshold
        if action.action_type == "delete_file":
            targets = action.parameters.get("files", [])
            if len(targets) >= settings.MAX_BULK_DELETE_THRESHOLD:
                return True

        return False

    def create_confirmation_request(self, step: Step) -> str:
        """
        Registers a step requiring confirmation and generates a token.

        Args:
            step (Step): Step requiring confirmation.

        Returns:
            str: Token ID for confirmation matching.
        """
        token = str(uuid.uuid4())
        self._pending_tokens[token] = step
        logger.info(
            f"Sensitive action detected for step '{step.step_id}' ({step.action.action_type}). Created confirmation token '{token}'",
            extra={"audit": True},
        )
        return token

    def confirm_action(self, token: str) -> bool:
        """
        Approves a pending token.

        Args:
            token (str): Confirmation token ID.

        Returns:
            bool: True if token was valid and approved.
        """
        if token in self._pending_tokens:
            del self._pending_tokens[token]
            self._approved_tokens.add(token)
            logger.info(f"Token '{token}' approved by user", extra={"audit": True})
            return True
        logger.warning(f"Attempted to confirm invalid or expired token '{token}'")
        return False

    def is_approved(self, token: str) -> bool:
        """Checks if token has been confirmed."""
        return token in self._approved_tokens

    def get_pending_tokens(self) -> Dict[str, Any]:
        """Returns dict of active pending tokens requiring confirmation."""
        result = {}
        for token, step in self._pending_tokens.items():
            result[token] = {
                "token": token,
                "step_id": step.step_id,
                "description": step.description,
                "agent_name": step.action.agent_name,
                "action_type": step.action.action_type,
                "parameters": step.action.parameters,
            }
        return result

