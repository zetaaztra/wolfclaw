"""
Bot Export/Import — portable .wolfbot JSON files.
"""
import json
from fastapi import APIRouter, HTTPException, Request
from core.local_db import _get_connection
from auth.supabase_client import get_current_user

router = APIRouter()

@router.get("/bots/{bot_id}/export")
async def export_bot(bot_id: str):
    """Export a bot as a portable .wolfbot JSON."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM bots WHERE id = ?", (bot_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Bot not found")

    wolfbot = {
        "wolfbot_version": "1.0",
        "name": row["name"],
        "model": row["model"],
        "system_prompt": row["prompt"],
        "fallback_models": json.loads(row["fallback_models"]) if row["fallback_models"] else [],
        "user_context": row.get("user_context", ""),
        "memory": row.get("memory", ""),
    }
    return wolfbot

@router.post("/bots/import")
async def import_bot(request: Request):
    """Import a bot from a .wolfbot JSON payload."""
    import uuid
    body = await request.json()

    if "name" not in body or "system_prompt" not in body:
        raise HTTPException(status_code=400, detail="Invalid .wolfbot format: needs 'name' and 'system_prompt'.")

    user = get_current_user()
    user_id = user["id"] if user else "local_user"

    # Get or create workspace
    conn = _get_connection()
    ws_row = conn.execute("SELECT id FROM workspaces WHERE user_id = ?", (user_id,)).fetchone()
    if not ws_row:
        raise HTTPException(status_code=400, detail="No workspace found.")

    ws_id = ws_row["id"]
    new_id = str(uuid.uuid4())
    fallbacks = json.dumps(body.get("fallback_models", []))

    conn.execute(
        "INSERT INTO bots (id, workspace_id, name, model, prompt, fallback_models) VALUES (?, ?, ?, ?, ?, ?)",
        (new_id, ws_id, body["name"], body.get("model", "nvidia/llama-3.1-70b-instruct"), body["system_prompt"], fallbacks)
    )
    conn.commit()

    return {"status": "imported", "bot_id": new_id, "name": body["name"]}
