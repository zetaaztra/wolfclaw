import json
import logging
from typing import Callable, Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)

class EventBus:
    """
    A lightweight PUB/SUB system for the Wolfclaw pack.
    Enables bots to 'ping' each other and subscribe to system events.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance.subscribers = defaultdict(list)
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable):
        """Allows a bot or module to listen for specific events."""
        self.subscribers[event_type].append(callback)
        logger.info(f"Subscribed to event: {event_type}")

    def publish(self, event_type: str, data: Dict):
        """Broadcasts an event to all subscribers."""
        logger.info(f"Publishing event: {event_type}")
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Event callback failed for {event_type}: {e}")

# Global access point
bus = EventBus()

def notify_pack(bot_name: str, message: str, data: Dict = None):
    """Helper to publish a bot-specific event."""
    bus.publish("bot_ping", {
        "from": bot_name,
        "message": message,
        "payload": data or {}
    })
