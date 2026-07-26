"""
Base Agent Abstract Implementation for JARVIS OS.
Enforces standard capabilities registration, action validation, and exception handling across all agents.
"""

from abc import ABC
from typing import List
from jarvis.core.interfaces import BaseAgent
from jarvis.core.models import AgentAction, ExecutionResult
from jarvis.utils.logger import get_logger

logger = get_logger("BaseAgent")


class AbstractAgent(BaseAgent, ABC):
    """
    Standard Base Agent providing capability registration and common validation routines.
    """

    async def validate_action(self, action: AgentAction) -> bool:
        """
        Validates if requested action type is supported by this agent.

        Args:
            action (AgentAction): Action payload.

        Returns:
            bool: True if supported.
        """
        if action.action_type not in self.capabilities:
            logger.warning(
                f"Agent '{self.name}' does not support action type '{action.action_type}'. Supported: {self.capabilities}"
            )
            return False
        return True
