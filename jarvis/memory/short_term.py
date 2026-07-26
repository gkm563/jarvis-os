"""
Short-Term In-Memory Session & Clipboard Store.
Volatile storage for active conversation context, transient task buffers, and clipboard snapshots.
"""

import time
from typing import Any, Dict, Optional
from jarvis.core.interfaces import BaseMemory
from jarvis.utils.logger import get_logger

logger = get_logger("ShortTermMemory")


class ShortTermMemory(BaseMemory):
    """
    In-memory context key-value store with support for TTL expiration.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Retrieves a value if key exists and has not expired."""
        if key not in self._store:
            return None

        entry = self._store[key]
        expiry = entry.get("expiry")
        if expiry and time.time() > expiry:
            del self._store[key]
            logger.debug(f"Expired key '{key}' purged from short-term memory")
            return None

        return entry.get("value")

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Stores a key-value pair with optional TTL."""
        expiry = time.time() + ttl_seconds if ttl_seconds else None
        self._store[key] = {"value": value, "expiry": expiry}
        logger.debug(f"Stored key '{key}' in short-term memory (TTL: {ttl_seconds}s)")

    async def delete(self, key: str) -> None:
        """Removes a key from short-term memory."""
        if key in self._store:
            del self._store[key]
            logger.debug(f"Deleted key '{key}' from short-term memory")
