"""
Anomaly Monitor & Process Sandbox Module.
Tracks execution anomalies and isolates suspect agents to protect host OS.
"""

import time
from typing import Dict, List
from jarvis.utils.logger import get_logger

logger = get_logger("AnomalyMonitor")


class AnomalyMonitor:
    """
    Monitors agent call frequency, error rates, and resource usage thresholds.
    """

    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls_per_minute = max_calls_per_minute
        self._action_timestamps: Dict[str, List[float]] = {}
        self._sandboxed_agents: Dict[str, str] = {}

    def record_agent_action(self, agent_name: str) -> bool:
        """
        Records an action invocation and returns False if anomaly threshold is exceeded.

        Args:
            agent_name (str): Agent identifier.

        Returns:
            bool: True if agent behavior is within normal parameters.
        """
        if agent_name in self._sandboxed_agents:
            logger.error(
                f"Action blocked: Agent '{agent_name}' is currently sandboxed: {self._sandboxed_agents[agent_name]}",
                extra={"audit": True},
            )
            return False

        now = time.time()
        if agent_name not in self._action_timestamps:
            self._action_timestamps[agent_name] = []

        # Keep timestamps from the last 60 seconds
        self._action_timestamps[agent_name] = [
            ts for ts in self._action_timestamps[agent_name] if now - ts < 60
        ]
        self._action_timestamps[agent_name].append(now)

        # Check call rate
        call_count = len(self._action_timestamps[agent_name])
        if call_count > self.max_calls_per_minute:
            self.sandbox_agent(
                agent_name, f"Exceeded maximum action rate threshold ({call_count}/min)"
            )
            return False

        return True

    def sandbox_agent(self, agent_name: str, reason: str) -> None:
        """Isolates an agent from performing further actions."""
        self._sandboxed_agents[agent_name] = reason
        logger.critical(
            f"ANOMALY DETECTED: Agent '{agent_name}' has been SANDBOXED. Reason: {reason}",
            extra={"audit": True},
        )

    def is_sandboxed(self, agent_name: str) -> bool:
        """Returns True if agent is sandboxed."""
        return agent_name in self._sandboxed_agents

    def release_sandbox(self, agent_name: str) -> None:
        """Releases an agent from sandbox after review."""
        if agent_name in self._sandboxed_agents:
            del self._sandboxed_agents[agent_name]
            logger.info(f"Agent '{agent_name}' released from sandbox", extra={"audit": True})
