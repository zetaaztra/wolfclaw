"""
Phase 14 — Notification Center
Thread-safe in-memory notification store with read/unread tracking.
"""
import threading
from datetime import datetime
from collections import deque

class NotificationCenter:
    """Central notification system for background agent events."""

    def __init__(self, max_notifications=200):
        self._lock = threading.Lock()
        self._notifications = deque(maxlen=max_notifications)
        self._unread_count = 0

    def push(self, title: str, body: str, category: str = "info", source: str = "system"):
        """Push a new notification."""
        with self._lock:
            notif = {
                "id": len(self._notifications),
                "title": title,
                "body": body,
                "category": category,  # info, success, warning, error
                "source": source,      # proactive_agent, clipboard, scheduler, flow, etc.
                "ts": datetime.utcnow().isoformat(),
                "read": False
            }
            self._notifications.appendleft(notif)
            self._unread_count += 1
            return notif

    def get_all(self, limit: int = 50) -> list:
        with self._lock:
            return list(self._notifications)[:limit]

    def get_unread_count(self) -> int:
        with self._lock:
            return self._unread_count

    def mark_all_read(self):
        with self._lock:
            for n in self._notifications:
                n["read"] = True
            self._unread_count = 0

    def mark_read(self, notif_id: int):
        with self._lock:
            for n in self._notifications:
                if n["id"] == notif_id and not n["read"]:
                    n["read"] = True
                    self._unread_count = max(0, self._unread_count - 1)
                    break

    def clear(self):
        with self._lock:
            self._notifications.clear()
            self._unread_count = 0

# Singleton
notifications = NotificationCenter()

# Auto-subscribe to EventBus for background events
try:
    from core.bus import bus
    def _on_event(event_name, data):
        title_map = {
            "flow_executed": "Flow Completed",
            "bot_ping": "Bot Activity",
            "macro_recorded": "Macro Recorded",
            "clipboard_change": "Clipboard Updated",
            "plugin_installed": "Plugin Installed",
            "swarm_completed": "Swarm Finished",
            "webhook_triggered": "Webhook Fired",
        }
        title = title_map.get(event_name, event_name.replace("_", " ").title())
        body = str(data)[:200] if data else ""
        notifications.push(title, body, category="info", source=event_name)

    for evt in ["flow_executed", "bot_ping", "macro_recorded", "clipboard_change",
                 "plugin_installed", "swarm_completed", "webhook_triggered"]:
        bus.subscribe(evt, lambda data, en=evt: _on_event(en, data))
except Exception:
    pass
