"""
Dynamic Step Reasoner for JARVIS OS.
Evaluates runtime state and decides dynamic replanning or parameter adjustments.
"""

from typing import Any, Dict, Optional
from jarvis.core.models import Step, ExecutionResult
from jarvis.utils.logger import get_logger

logger = get_logger("StepReasoner")


class StepReasoner:
    """
    Evaluates step execution results and suggests adjustments or replanning.
    """

    def evaluate_step_result(self, step: Step, result: ExecutionResult) -> Dict[str, Any]:
        """
        Evaluates step outcome to determine if execution can proceed or needs retry/replanning.

        Args:
            step (Step): Executed step object.
            result (ExecutionResult): Execution result from agent.

        Returns:
            Dict[str, Any]: Recommendation payload.
        """
        if result.success:
            logger.debug(f"Step '{step.step_id}' evaluated SUCCESSFUL")
            return {"action": "continue", "next_step": None}

        logger.warning(
            f"Step '{step.step_id}' evaluated FAILURE ({result.error_message}). Evaluating recovery strategy."
        )

        if step.retry_count < step.max_retries:
            return {
                "action": "retry",
                "attempt": step.retry_count + 1,
                "reason": result.error_message,
            }

        return {
            "action": "fail",
            "reason": f"Max retries ({step.max_retries}) exceeded: {result.error_message}",
        }
