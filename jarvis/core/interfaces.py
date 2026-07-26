"""
Abstract Base Classes and Interfaces for JARVIS OS.
Follows Dependency Inversion Principle (DIP) to allow loose coupling between layers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from jarvis.core.models import AgentAction, ExecutionResult, Plan, UserProfile


class BaseAgent(ABC):
    """Abstract interface that all domain agents must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the agent."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief summary of the agent's capabilities."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """List of supported action types."""
        pass

    @abstractmethod
    async def execute(self, action: AgentAction) -> ExecutionResult:
        """
        Executes a domain action assigned to this agent.

        Args:
            action (AgentAction): Action parameters and type.

        Returns:
            ExecutionResult: Standardized execution result.
        """
        pass

    @abstractmethod
    async def validate_action(self, action: AgentAction) -> bool:
        """Validates if action parameters are well-formed and actionable."""
        pass


class BaseTool(ABC):
    """Interface for modular tools used by agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        pass


class BaseMemory(ABC):
    """Interface for Memory storage implementations."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass


class BaseLLMProvider(ABC):
    """Interface for LLM reasoning backends."""

    @abstractmethod
    async def generate_response(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> str:
        pass

    @abstractmethod
    async def generate_plan(self, user_goal: str, context: Optional[str] = None) -> Plan:
        pass


class BaseSecurityVault(ABC):
    """Interface for secure secret vault storage."""

    @abstractmethod
    def store_secret(self, service: str, secret: str) -> bool:
        pass

    @abstractmethod
    def get_secret(self, service: str) -> Optional[str]:
        pass

    @abstractmethod
    def delete_secret(self, service: str) -> bool:
        pass
