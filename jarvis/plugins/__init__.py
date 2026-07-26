"""
Plugin Package Initialization.
"""

from jarvis.plugins.sdk import PluginManifest, BasePlugin
from jarvis.plugins.loader import PluginLoader

plugin_loader = PluginLoader()

__all__ = ["PluginManifest", "BasePlugin", "PluginLoader", "plugin_loader"]
