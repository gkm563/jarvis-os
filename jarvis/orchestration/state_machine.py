"""
Task State Machine Module for JARVIS OS.
Tracks state transitions and validation rules for Plan and Step lifecycle.
"""

from typing import Dict, Set
from jarvis.core.models import StepStatus, PlanStatus, Step, Plan
from jarvis.core.exceptions import ExecutionError
from jarvis.utils.logger import get_logger

logger = get_logger("StateMachine")


class PlanStateMachine:
    """
    Manages valid state transitions for Plans and Steps in execution DAGs.
    """

    VALID_STEP_TRANSITIONS: Dict[StepStatus, Set[StepStatus]] = {
        StepStatus.PENDING: {StepStatus.RUNNING, StepStatus.SKIPPED},
        StepStatus.RUNNING: {
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.WAITING_FOR_CONFIRMATION,
        },
        StepStatus.WAITING_FOR_CONFIRMATION: {
            StepStatus.RUNNING,
            StepStatus.FAILED,
            StepStatus.SKIPPED,
        },
        StepStatus.FAILED: {StepStatus.RUNNING, StepStatus.ROLLED_BACK},
        StepStatus.COMPLETED: set(),
        StepStatus.SKIPPED: set(),
        StepStatus.ROLLED_BACK: set(),
    }

    def transition_step(self, step: Step, new_status: StepStatus) -> None:
        """
        Transitions a step to a new status if valid.

        Args:
            step (Step): Step instance.
            new_status (StepStatus): Target status.

        Raises:
            ExecutionError: If state transition is illegal.
        """
        allowed = self.VALID_STEP_TRANSITIONS.get(step.status, set())
        if new_status not in allowed:
            raise ExecutionError(
                step.step_id,
                f"Illegal state transition from '{step.status.value}' to '{new_status.value}'",
            )

        logger.debug(f"Step '{step.step_id}' state transitioned: {step.status.value} -> {new_status.value}")
        step.status = new_status
