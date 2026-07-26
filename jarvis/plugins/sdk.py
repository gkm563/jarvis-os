"""
Plugin Developer SDK for JARVIS OS.
Provides interfaces and models for third-party plugin extensions (Figma, Notion, Slack, Jira, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel


class PluginManifest(BaseModel):
    """Manifest describing third-party plugin attributes and requested permission scopes."""
    plugin_id: str
    name: str
    version: str
    author: str
    required_permissions: List[str]
    entry_point: str


class BasePlugin(ABC):
    """Abstract interface for external plugins."""

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        pass

    @abstractmethod
    async def execute_plugin_action(self, action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        pass
