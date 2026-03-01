import os
import time
import logging
import psutil
import threading
from typing import Dict

logger = logging.getLogger(__name__)

class ContextualHeartbeat:
    """
    Monitors machine state to ensure 'Sovereign Safety'.
    Prevents the agent from performing actions if the user is active.
    """
    
    def __init__(self):
        self.last_user_activity = time.time()
        self.current_app = ""
        self.is_user_active = False
        self._stop_event = threading.Event()

    def start(self):
        """Starts monitoring in a background thread."""
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            try:
                # 1. Check CPU load
                cpu_usage = psutil.cpu_percent(interval=None)
                
                # 2. Simulated mouse/keyboard check
                # In production, we'd use pynput or OS-specific APIs
                self.is_user_active = cpu_usage > 50 # Simplified proxy
                
                # 3. Get Active Window (Simulated)
                self.current_app = "VS Code" if self.is_user_active else "Idle"
                
                time.sleep(2)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                time.sleep(5)

    def is_safe_to_execute(self) -> bool:
        """Returns True if the bot won't interfere with the user."""
        return not self.is_user_active

    def get_system_status(self) -> Dict:
        return {
            "is_user_active": self.is_user_active,
            "current_app": self.current_app,
            "cpu_pulse": psutil.cpu_percent()
        }

# Singleton
heartbeat = ContextualHeartbeat()
heartbeat.start()
