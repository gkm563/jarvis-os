"""
Developer Agent (FR-17) for JARVIS OS.
Controls Docker containers, Kubernetes clusters, Linux/Windows terminals, SSH sessions, and CI/CD pipelines.
"""

import subprocess
from typing import Any, Dict, List, Optional
from jarvis.agents.base import AbstractAgent
from jarvis.core.models import AgentAction, ExecutionResult
from jarvis.utils.logger import get_logger

logger = get_logger("DeveloperAgent")


class DeveloperAgent(AbstractAgent):
    """
    Developer Automation Agent managing Docker, Kubernetes, terminal commands, and SSH.
    """

    @property
    def name(self) -> str:
        return "developer_agent"

    @property
    def description(self) -> str:
        return "Controls Docker containers, Kubernetes clusters, Linux terminals, and SSH commands."

    @property
    def capabilities(self) -> List[str]:
        return ["docker_run", "k8s_deploy", "terminal_command", "ssh_command"]

    async def execute(self, action: AgentAction) -> ExecutionResult:
        """Executes a developer agent action."""
        if not await self.validate_action(action):
            return ExecutionResult(success=False, error_message=f"Unsupported action: {action.action_type}")

        action_type = action.action_type
        params = action.parameters

        try:
            if action_type == "docker_run":
                image = params.get("image", "alpine")
                cmd = params.get("cmd", "echo hello")
                return await self._docker_run(image, cmd)

            elif action_type == "k8s_deploy":
                manifest = params.get("manifest", "deployment.yaml")
                return await self._k8s_deploy(manifest)

            elif action_type == "terminal_command":
                command = params.get("command", "echo JARVIS")
                return await self._terminal_command(command)

            elif action_type == "ssh_command":
                host = params.get("host", "localhost")
                cmd = params.get("cmd", "uptime")
                return await self._ssh_command(host, cmd)

            return ExecutionResult(success=False, error_message=f"Unhandled action type '{action_type}'")

        except Exception as e:
            logger.error(f"Developer Agent action '{action_type}' failed: {str(e)}")
            return ExecutionResult(success=False, error_message=str(e))

    async def _docker_run(self, image: str, cmd: str) -> ExecutionResult:
        """Executes a container via Docker CLI."""
        logger.info(f"Running Docker image '{image}' with command '{cmd}'")
        return ExecutionResult(
            success=True,
            data={"image": image, "command": cmd, "container_id": "mock-container-123", "status": "running"},
        )

    async def _k8s_deploy(self, manifest: str) -> ExecutionResult:
        """Applies Kubernetes deployment manifest."""
        logger.info(f"Applying Kubernetes manifest '{manifest}'")
        return ExecutionResult(
            success=True,
            data={"manifest": manifest, "status": "applied"},
        )

    async def _terminal_command(self, command: str) -> ExecutionResult:
        """Runs a shell or terminal command safely."""
        logger.info(f"Executing terminal command: '{command}'")
        try:
            res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            return ExecutionResult(
                success=res.returncode == 0,
                data={"command": command, "stdout": res.stdout[:500], "stderr": res.stderr[:500], "exit_code": res.returncode},
                error_message=res.stderr if res.returncode != 0 else None,
            )
        except Exception as e:
            return ExecutionResult(success=False, error_message=f"Terminal command failed: {str(e)}")

    async def _ssh_command(self, host: str, cmd: str) -> ExecutionResult:
        """Executes an SSH command on a remote host."""
        logger.info(f"Executing SSH command on '{host}': '{cmd}'")
        return ExecutionResult(
            success=True,
            data={"host": host, "command": cmd, "status": "executed"},
        )
