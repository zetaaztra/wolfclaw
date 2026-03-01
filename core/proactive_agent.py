import threading
import time
import logging
import core.local_db as local_db
from core.orchestrator import run_flow
from core.system_tools import SystemTools

logger = logging.getLogger(__name__)

class ProactiveAgent:
    """
    Background daemon that monitors the system and executes flows autonomously 
    without human intervention based on schedules or events.
    """
    def __init__(self):
        self._stop_event = threading.Event()
        self.thread = None
        self.polling_interval = 60 # Check events every 60 seconds
        self.tools = SystemTools()

    def start(self):
        if self.thread and self.thread.is_alive():
            logger.warning("ProactiveAgent already running.")
            return
            
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, name="ProactiveAgentThread", daemon=True)
        self.thread.start()
        logger.info("ProactiveAgent started.")

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
            logger.info("ProactiveAgent stopped.")

    def _run_loop(self):
        """Main background loop."""
        while not self._stop_event.is_set():
            try:
                self._check_triggers()
            except Exception as e:
                logger.error(f"ProactiveAgent error in run loop: {e}")
                
            self._stop_event.wait(self.polling_interval)

    def _check_triggers(self):
        """Check all registered automations/schedules and fire if needed."""
        # For now, we simulate checking scheduled flows
        # In a full implementation, we would query the local DB for active triggers
        workspace_id = "local_user" # Default
        workspace_db_id = local_db.get_or_create_workspace(workspace_id)
        
        # Example logic: if we had a table of proactive tasks, we'd query them here.
        # Since we are introducing this feature, we will log that the heartbeat is active.
        logger.debug("ProactiveAgent heartbeat check...")
        
        # You could extend this by reading "workflows/automation.json" or similar
        # and checking if any condition is met (e.g., CPU > 90%, New File in Folder).

proactive_daemon = ProactiveAgent()
