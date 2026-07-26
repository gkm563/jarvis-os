"""
Event Bus & Pub-Sub Infrastructure for JARVIS OS.
Enables decoupled, asynchronous event propagation across core components.
"""

import asyncio
from typing import Any, Callable, Dict, List
from pydantic import BaseModel
from jarvis.utils.logger import get_logger

logger = get_logger("EventBus")


class SystemEvent(BaseModel):
    """Base event payload for system message propagation."""
    event_type: str
    sender: str
    payload: Dict[str, Any]


class EventBus:
    """In-memory asynchronous event bus supporting topic subscriptions."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[SystemEvent], None]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[SystemEvent], None]):
        """
        Subscribes a callback function to a specific event type.

        Args:
            event_type (str): Event identifier topic.
            callback (Callable): Callback function invoked when event fires.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed callback {callback.__name__} to event topic '{event_type}'")

    async def publish(self, event: SystemEvent):
        """
        Publishes an event to all registered topic subscribers.

        Args:
            event (SystemEvent): System event instance.
        """
        subscribers = self._subscribers.get(event.event_type, [])
        logger.debug(f"Publishing event '{event.event_type}' from '{event.sender}' to {len(subscribers)} subscribers")
        for subscriber in subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event)
                else:
                    subscriber(event)
            except Exception as e:
                logger.error(f"Error executing event subscriber {subscriber.__name__}: {str(e)}")


# Global Event Bus Singleton
event_bus = EventBus()
