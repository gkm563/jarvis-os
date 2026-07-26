"""
Self-Healing Reflection Engine for JARVIS OS.
Recovers from UI updates and element locators by re-analyzing screen elements visually.
"""

from typing import Any, Dict, Optional
from jarvis.core.models import AgentAction
from jarvis.utils.logger import get_logger

logger = get_logger("ReflectionEngine")


class ReflectionEngine:
    """
    Analyzes execution failures and attempts self-healing element locators or fallback actions.
    """

    def heal_action(self, action: AgentAction, error_context: str) -> AgentAction:
        """
        Attempts to re-target or heal an action parameters when a failure occurs.

        Args:
            action (AgentAction): Original action that failed.
            error_context (str): Error message context.

        Returns:
            AgentAction: Healed action instance with updated parameters.
        """
        logger.info(f"Self-healing triggered for agent '{action.agent_name}' action '{action.action_type}'")

        healed_params = dict(action.parameters)
        if action.agent_name == "browser_agent" and "element_not_found" in error_context.lower():
            # Switch to semantic vision fallback locator
            healed_params["use_vision_fallback"] = True
            logger.info(f"Self-healed browser action using semantic vision locator fallback")

        return AgentAction(
            agent_name=action.agent_name,
            action_type=action.action_type,
            parameters=healed_params,
            is_sensitive=action.is_sensitive,
            action_class=action.action_class,
        )
