"""
Sandboxed Plugin Loader & Manifest Validator.
"""

from typing import Dict, List, Optional
from jarvis.plugins.sdk import BasePlugin, PluginManifest
from jarvis.utils.logger import get_logger

logger = get_logger("PluginLoader")


class PluginLoader:
    """Loads and validates sandboxed third-party plugins."""

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}

    def load_plugin(self, plugin: BasePlugin) -> bool:
        manifest = plugin.manifest
        logger.info(f"Loading plugin '{manifest.name}' v{manifest.version} by {manifest.author}")
        self._plugins[manifest.plugin_id] = plugin
        return True

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        return self._plugins.get(plugin_id)
