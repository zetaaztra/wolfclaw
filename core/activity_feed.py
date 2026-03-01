"""
Real-Time Activity Feed — logs all system events into a ring buffer
and publishes them through the EventBus.
"""
import logging
import threading
from datetime import datetime, timezone
from collections import deque
from typing import List, Dict

logger = logging.getLogger(__name__)

class ActivityFeed:
    """Thread-safe ring buffer that stores the last N system events."""

    def __init__(self, max_events: int = 200):
        self._events = deque(maxlen=max_events)
        self._lock = threading.Lock()
        self._subscribe_to_bus()

    def _subscribe_to_bus(self):
        """Auto-subscribe to the global EventBus so events flow in automatically."""
        try:
            from core.bus import bus
            bus.subscribe("bot_ping", lambda d: self.log_event("bot_ping", d.get("message", ""), d))
            bus.subscribe("flow_executed", lambda d: self.log_event("flow", d.get("name", "Flow"), d))
            bus.subscribe("macro_recorded", lambda d: self.log_event("macro", "Macro recorded", d))
            bus.subscribe("swarm_completed", lambda d: self.log_event("swarm", "Swarm finished", d))
            bus.subscribe("plugin_installed", lambda d: self.log_event("plugin", f"Installed {d.get('id','')}", d))
            logger.info("ActivityFeed subscribed to EventBus.")
        except Exception as e:
            logger.warning(f"ActivityFeed could not subscribe to EventBus: {e}")

    def log_event(self, event_type: str, detail: str, meta: Dict = None):
        """Push an event onto the ring buffer."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "detail": detail,
            "meta": meta or {}
        }
        with self._lock:
            self._events.appendleft(entry)

    def get_recent(self, limit: int = 50) -> List[Dict]:
        """Return the most recent events."""
        with self._lock:
            return list(self._events)[:limit]

# Singleton
activity_feed = ActivityFeed()
