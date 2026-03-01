"""
Clipboard Agent — monitors the system clipboard and optionally
processes copied text through a configured bot.
"""
import threading
import time
import logging

logger = logging.getLogger(__name__)

class ClipboardAgent:
    """Background daemon that watches the system clipboard for changes."""

    def __init__(self):
        self._stop_event = threading.Event()
        self.thread = None
        self._last_content = ""
        self.polling_interval = 2  # seconds

    def start(self):
        if self.thread and self.thread.is_alive():
            logger.warning("ClipboardAgent already running.")
            return

        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, name="ClipboardAgentThread", daemon=True)
        self.thread.start()
        logger.info("ClipboardAgent started.")

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
            logger.info("ClipboardAgent stopped.")

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self._check_clipboard()
            except Exception as e:
                logger.debug(f"ClipboardAgent check error: {e}")
            self._stop_event.wait(self.polling_interval)

    def _check_clipboard(self):
        """Check if clipboard content has changed."""
        try:
            import pyperclip
            current = pyperclip.paste()
        except ImportError:
            # pyperclip not installed — fallback silently
            return
        except Exception:
            return

        if current and current != self._last_content:
            self._last_content = current
            logger.info(f"ClipboardAgent detected new content ({len(current)} chars).")

            # Publish to EventBus
            try:
                from core.bus import bus
                bus.publish("clipboard_change", {
                    "content": current[:500],  # Cap at 500 chars for safety
                    "length": len(current)
                })
            except Exception as e:
                logger.debug(f"Could not publish clipboard event: {e}")

            # Log to activity feed
            try:
                from core.activity_feed import activity_feed
                preview = current[:80].replace("\n", " ")
                activity_feed.log_event("clipboard", f"New clipboard: {preview}...")
            except Exception:
                pass

clipboard_agent = ClipboardAgent()
