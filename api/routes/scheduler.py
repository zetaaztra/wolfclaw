"""
Wolfclaw V3 — Scheduled Tasks API Routes (Phase 14)

Create, manage, and execute recurring AI tasks.
"""

import os
import threading
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core import local_db
from core.bot_manager import _get_active_workspace_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


# ─────────── Models ───────────

class CreateTaskRequest(BaseModel):
    bot_id: str
    name: str
    prompt: str
    schedule_type: str = "interval"  # "interval" or "cron"
    schedule_value: str = "60"       # minutes for interval, cron expression for cron


class UpdateTaskRequest(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_value: Optional[str] = None
    is_active: Optional[int] = None


# ─────────── CRUD ───────────

@router.post("/tasks")
async def create_task(req: CreateTaskRequest):
    """Create a new scheduled task."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Restricted to Desktop.")
    try:
        ws_id = _get_active_workspace_id()
        task_id = local_db.create_scheduled_task(
            ws_id=ws_id,
            bot_id=req.bot_id,
            name=req.name,
            prompt=req.prompt,
            schedule_type=req.schedule_type,
            schedule_value=req.schedule_value
        )
        
        # Register with the scheduler if it's running
        _register_task_with_scheduler(task_id)
        
        return {"status": "success", "task_id": task_id, "message": f"✅ Task '{req.name}' created."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def list_tasks():
    """List all scheduled tasks."""
    try:
        ws_id = _get_active_workspace_id()
        tasks = local_db.get_scheduled_tasks(ws_id)
        return {"status": "success", "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tasks/{task_id}")
async def update_task(task_id: str, req: UpdateTaskRequest):
    """Update a scheduled task."""
    try:
        updates = {k: v for k, v in req.dict().items() if v is not None}
        if updates:
            local_db.update_scheduled_task(task_id, **updates)
            _register_task_with_scheduler(task_id)  # re-register with new config
        return {"status": "success", "message": "Task updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a scheduled task."""
    try:
        _unregister_task(task_id)
        local_db.delete_scheduled_task(task_id)
        return {"status": "success", "message": "Task deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/run")
async def run_task_now(task_id: str):
    """Manually trigger a task immediately."""
    try:
        task = local_db.get_scheduled_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")
        
        # Execute in a background thread to not block
        t = threading.Thread(target=_execute_task, args=(task,), daemon=True)
        t.start()
        
        return {"status": "success", "message": f"Task '{task['name']}' triggered."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/results")
async def get_task_results(task_id: str):
    """Get execution history for a task."""
    try:
        results = local_db.get_task_results(task_id)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────── SCHEDULER ENGINE ───────────

_scheduler = None

def _get_scheduler():
    """Lazy-init the APScheduler instance."""
    global _scheduler
    if _scheduler is None:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            _scheduler = BackgroundScheduler()
            _scheduler.start()
            logger.info("APScheduler started.")
            
            # Load and register all active tasks in a background thread
            def _load_all_tasks():
                try:
                    ws_id = _get_active_workspace_id()
                    tasks = local_db.get_scheduled_tasks(ws_id)
                    for task in tasks:
                        if task.get('is_active'):
                            _register_task_with_scheduler(task['id'])
                except:
                    pass
            
            import threading
            threading.Thread(target=_load_all_tasks, daemon=True).start()
                
        except ImportError:
            logger.warning("apscheduler not installed. Scheduled tasks will only work with manual trigger.")
            return None
    return _scheduler


def _register_task_with_scheduler(task_id: str):
    """Register or update a task in the scheduler."""
    sched = _get_scheduler()
    if not sched:
        return
    
    task = local_db.get_scheduled_task(task_id)
    if not task:
        return
    
    job_id = f"wolfclaw_task_{task_id}"
    
    # Remove existing job if any
    try:
        sched.remove_job(job_id)
    except:
        pass
    
    if not task.get('is_active'):
        return
    
    try:
        if task['schedule_type'] == 'interval':
            minutes = int(task['schedule_value'])
            sched.add_job(
                _execute_task,
                'interval',
                minutes=minutes,
                id=job_id,
                args=[task],
                replace_existing=True
            )
            logger.info(f"Registered task '{task['name']}' to run every {minutes} minutes.")
        elif task['schedule_type'] == 'cron':
            # Parse cron expression: minute hour day_of_month month day_of_week
            parts = task['schedule_value'].split()
            if len(parts) >= 5:
                sched.add_job(
                    _execute_task,
                    'cron',
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                    id=job_id,
                    args=[task],
                    replace_existing=True
                )
                logger.info(f"Registered cron task '{task['name']}' with schedule {task['schedule_value']}.")
    except Exception as e:
        logger.error(f"Failed to register task {task_id}: {e}")


def _unregister_task(task_id: str):
    """Remove a task from the scheduler."""
    sched = _get_scheduler()
    if not sched:
        return
    try:
        sched.remove_job(f"wolfclaw_task_{task_id}")
    except:
        pass


def _execute_task(task: dict):
    """Execute a scheduled task by sending the prompt to the bot's AI model."""
    try:
        from core.llm_engine import WolfEngine
        from core import bot_manager
        
        bots = bot_manager.get_bots()
        bot_id = task['bot_id']
        
        if bot_id not in bots:
            local_db.save_task_result(task['id'], f"❌ Bot {bot_id} not found.")
            return
        
        bot = bots[bot_id]
        engine = WolfEngine(bot['model'], fallback_models=bot.get('fallback_models', []))
        
        messages = [{"role": "user", "content": task['prompt']}]
        response = engine.chat(
            messages=messages,
            system_prompt=bot['prompt'],
            bot_id=bot_id
        )
        
        reply = response.choices[0].message.content or "(No response)"
        local_db.save_task_result(task['id'], reply)
        logger.info(f"Task '{task['name']}' executed successfully.")
        
    except Exception as e:
        error_msg = f"❌ Execution failed: {str(e)}"
        try:
            local_db.save_task_result(task['id'], error_msg)
        except:
            pass
        logger.error(f"Task execution error: {e}")


# Auto-start scheduler on import
# try:
#     _get_scheduler()
# except:
#     pass
