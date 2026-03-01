"""
Phase 14 — Pinned Prompts API
Save, list, and delete favorite prompts for one-click re-use.
"""
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.local_db import _get_connection

router = APIRouter()

def _ensure_table():
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pinned_prompts (
            id TEXT PRIMARY KEY,
            ws_id TEXT DEFAULT 'local',
            label TEXT NOT NULL,
            prompt TEXT NOT NULL,
            bot_id TEXT,
            icon TEXT DEFAULT '⭐',
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

class PinPromptRequest(BaseModel):
    label: str
    prompt: str
    bot_id: str = ""
    icon: str = "⭐"

@router.post("/pinned-prompts")
async def pin_prompt(req: PinPromptRequest):
    _ensure_table()
    pin_id = str(uuid.uuid4())
    conn = _get_connection()
    conn.execute(
        "INSERT INTO pinned_prompts (id, label, prompt, bot_id, icon) VALUES (?, ?, ?, ?, ?)",
        (pin_id, req.label, req.prompt, req.bot_id, req.icon)
    )
    conn.commit()
    return {"id": pin_id, "label": req.label, "status": "pinned"}

@router.get("/pinned-prompts")
async def list_pinned():
    _ensure_table()
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM pinned_prompts ORDER BY sort_order, created_at DESC").fetchall()
    return {"prompts": [dict(r) for r in rows]}

@router.delete("/pinned-prompts/{pin_id}")
async def unpin_prompt(pin_id: str):
    conn = _get_connection()
    conn.execute("DELETE FROM pinned_prompts WHERE id = ?", (pin_id,))
    conn.commit()
    return {"status": "unpinned"}
