"""
Webhook Triggers — allows external services to trigger saved Flows via unique URLs.
"""
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.local_db import _get_connection

router = APIRouter()

# ── DB helpers ──────────────────────────────────────────────
def _ensure_webhooks_table():
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS webhooks (
            id TEXT PRIMARY KEY,
            flow_id TEXT NOT NULL,
            label TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

_ensure_webhooks_table()

class WebhookCreate(BaseModel):
    flow_id: str
    label: str = ""

@router.post("/webhooks/create")
async def create_webhook(req: WebhookCreate):
    hook_id = str(uuid.uuid4())
    conn = _get_connection()
    conn.execute("INSERT INTO webhooks (id, flow_id, label) VALUES (?, ?, ?)",
                 (hook_id, req.flow_id, req.label))
    conn.commit()
    return {"id": hook_id, "url": f"/api/hooks/{hook_id}", "flow_id": req.flow_id}

@router.get("/webhooks")
async def list_webhooks():
    conn = _get_connection()
    rows = conn.execute("SELECT id, flow_id, label, created_at FROM webhooks").fetchall()
    return {"webhooks": [dict(r) for r in rows]}

@router.delete("/webhooks/{hook_id}")
async def delete_webhook(hook_id: str):
    conn = _get_connection()
    conn.execute("DELETE FROM webhooks WHERE id = ?", (hook_id,))
    conn.commit()
    return {"status": "deleted"}

@router.post("/hooks/{hook_id}")
async def trigger_webhook(hook_id: str):
    """The public endpoint that external services POST to."""
    conn = _get_connection()
    row = conn.execute("SELECT flow_id FROM webhooks WHERE id = ?", (hook_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found")

    flow_id = row["flow_id"]

    # Fetch the flow and execute it
    from core.local_db import get_flow
    flow = get_flow(flow_id) if callable(globals().get("get_flow")) else None

    # Try importing from local_db directly
    try:
        flow_row = conn.execute("SELECT * FROM flows WHERE id = ?", (flow_id,)).fetchone()
        if not flow_row:
            raise HTTPException(status_code=404, detail=f"Flow {flow_id} not found")

        from core.activity_feed import activity_feed
        activity_feed.log_event("webhook", f"Webhook {hook_id} triggered flow {flow_id}")

        return {"status": "triggered", "flow_id": flow_id, "hook_id": hook_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
