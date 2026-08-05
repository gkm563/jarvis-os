"""
Scheduler Agent (FR-20) for JARVIS OS.
Manages calendar events, daily routines, reminders, and deadline alerts.
"""

from typing import Any, Dict, List, Optional
from jarvis.agents.base import AbstractAgent
from jarvis.core.models import AgentAction, ExecutionResult
from jarvis.utils.logger import get_logger

logger = get_logger("SchedulerAgent")


class SchedulerAgent(AbstractAgent):
    """
    Scheduler Agent managing calendars, reminders, and automated routines.
    """

    @property
    def name(self) -> str:
        return "scheduler_agent"

    @property
    def description(self) -> str:
        return "Manages calendar meetings, daily routines, reminders, and deadline alerts."

    @property
    def capabilities(self) -> List[str]:
        return ["add_event", "set_reminder", "get_schedule"]

    async def execute(self, action: AgentAction) -> ExecutionResult:
        """Executes a scheduler agent action."""
        if not await self.validate_action(action):
            return ExecutionResult(success=False, error_message=f"Unsupported action: {action.action_type}")

        action_type = action.action_type
        params = action.parameters

        try:
            if action_type == "add_event":
                title = params.get("title", "Meeting")
                time_str = params.get("time", "Tomorrow 10:00 AM")
                return await self._add_event(title, time_str)

            elif action_type == "set_reminder":
                message = params.get("message", "Task Reminder")
                remind_at = params.get("remind_at", "In 1 hour")
                return await self._set_reminder(message, remind_at)

            elif action_type == "get_schedule":
                date_str = params.get("date", "Today")
                return await self._get_schedule(date_str)

            return ExecutionResult(success=False, error_message=f"Unhandled action type '{action_type}'")

        except Exception as e:
            logger.error(f"Scheduler Agent action '{action_type}' failed: {str(e)}")
            return ExecutionResult(success=False, error_message=str(e))

    async def _add_event(self, title: str, time_str: str) -> ExecutionResult:
        """Creates a calendar event."""
        logger.info(f"Adding calendar event '{title}' at '{time_str}'")
        return ExecutionResult(
            success=True,
            data={"title": title, "time": time_str, "status": "scheduled"},
        )

    async def _set_reminder(self, message: str, remind_at: str) -> ExecutionResult:
        """Sets a timer or reminder alert."""
        logger.info(f"Setting reminder: '{message}' at '{remind_at}'")
        return ExecutionResult(
            success=True,
            data={"message": message, "remind_at": remind_at, "status": "active"},
        )

    async def _get_schedule(self, date_str: str) -> ExecutionResult:
        """Retrieves schedule agenda for a specific day."""
        logger.info(f"Retrieving schedule agenda for '{date_str}'")
        mock_schedule = [
            {"time": "09:00 AM", "event": "JARVIS OS Daily Standup"},
            {"time": "02:00 PM", "event": "Architecture Review"},
        ]
        return ExecutionResult(
            success=True,
            data={"date": date_str, "events": mock_schedule, "count": len(mock_schedule)},
        )
