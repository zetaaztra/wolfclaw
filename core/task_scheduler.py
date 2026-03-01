"""
Scheduler — cron-like recurring task execution engine.
Reads scheduled_tasks from local_db and fires them when due.
"""
import threading
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TaskScheduler:
    """Background daemon that checks scheduled tasks and executes them when due."""

    def __init__(self):
        self._stop_event = threading.Event()
        self.thread = None
        self.check_interval = 60  # Check every 60 seconds

    def start(self):
        if self.thread and self.thread.is_alive():
            logger.warning("TaskScheduler already running.")
            return
        self._ensure_table()
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, name="TaskSchedulerThread", daemon=True)
        self.thread.start()
        logger.info("TaskScheduler started.")

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
            logger.info("TaskScheduler stopped.")

    def _ensure_table(self):
        from core.local_db import _get_connection
        conn = _get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                ws_id TEXT,
                name TEXT NOT NULL,
                cron_expr TEXT NOT NULL DEFAULT '0 * * * *',
                action_type TEXT NOT NULL DEFAULT 'flow',
                action_id TEXT NOT NULL,
                last_run TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self._check_tasks()
            except Exception as e:
                logger.error(f"TaskScheduler error: {e}")
            self._stop_event.wait(self.check_interval)

    def _check_tasks(self):
        """Check all enabled tasks and see if any are due."""
        from core.local_db import _get_connection
        conn = _get_connection()
        rows = conn.execute(
            "SELECT id, name, cron_expr, action_type, action_id, last_run FROM scheduled_tasks WHERE enabled = 1"
        ).fetchall()

        now = datetime.utcnow()
        for row in rows:
            if self._is_due(row["cron_expr"], row["last_run"], now):
                logger.info(f"Scheduler firing task: {row['name']}")
                self._execute_task(row)
                conn.execute("UPDATE scheduled_tasks SET last_run = ? WHERE id = ?",
                             (now.isoformat(), row["id"]))
                conn.commit()

    def _is_due(self, cron_expr: str, last_run: str, now: datetime) -> bool:
        """Simple interval-based check. Supports: 'every_Xm' for every X minutes."""
        if not cron_expr:
            return False

        # Simple format: "every_60m" means every 60 minutes
        if cron_expr.startswith("every_") and cron_expr.endswith("m"):
            try:
                interval_min = int(cron_expr[6:-1])
            except ValueError:
                return False
            if not last_run:
                return True
            try:
                last = datetime.fromisoformat(last_run)
                elapsed = (now - last).total_seconds() / 60
                return elapsed >= interval_min
            except ValueError:
                return True

        return False

    def _execute_task(self, task_row):
        """Execute the scheduled action."""
        try:
            from core.activity_feed import activity_feed
            activity_feed.log_event("scheduler", f"Scheduled task fired: {task_row['name']}")
        except Exception:
            pass

task_scheduler = TaskScheduler()
