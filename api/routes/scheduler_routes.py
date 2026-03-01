"""
Scheduler Routes — CRUD API for managing scheduled/recurring tasks.
"""
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.local_db import _get_connection

router = APIRouter()

class ScheduledTaskCreate(BaseModel):
    name: str
    cron_expr: str = "every_60m"
    action_type: str = "flow"
    action_id: str
    ws_id: str = "local"

@router.post("/scheduled-tasks")
async def create_scheduled_task(req: ScheduledTaskCreate):
    task_id = str(uuid.uuid4())
    conn = _get_connection()
    conn.execute(
        "INSERT INTO scheduled_tasks (id, ws_id, name, cron_expr, action_type, action_id) VALUES (?, ?, ?, ?, ?, ?)",
        (task_id, req.ws_id, req.name, req.cron_expr, req.action_type, req.action_id)
    )
    conn.commit()
    return {"id": task_id, "name": req.name, "status": "created"}

@router.get("/scheduled-tasks")
async def list_scheduled_tasks():
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM scheduled_tasks ORDER BY created_at DESC").fetchall()
    return {"tasks": [dict(r) for r in rows]}

@router.delete("/scheduled-tasks/{task_id}")
async def delete_scheduled_task(task_id: str):
    conn = _get_connection()
    conn.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
    conn.commit()
    return {"status": "deleted"}

@router.put("/scheduled-tasks/{task_id}/toggle")
async def toggle_scheduled_task(task_id: str):
    conn = _get_connection()
    row = conn.execute("SELECT enabled FROM scheduled_tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    new_state = 0 if row["enabled"] else 1
    conn.execute("UPDATE scheduled_tasks SET enabled = ? WHERE id = ?", (new_state, task_id))
    conn.commit()
    return {"status": "toggled", "enabled": bool(new_state)}
