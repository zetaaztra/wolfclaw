"""
Phase 14 — Onboarding Wizard API
Tracks first-run state and provides guided setup steps.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from core.local_db import _get_connection, get_key_local
from core.bot_manager import _get_active_workspace_id

router = APIRouter()

def _ensure_table():
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()

@router.get("/onboarding/status")
async def onboarding_status():
    """Check which onboarding steps are complete."""
    _ensure_table()
    conn = _get_connection()

    # Step 1: API key configured?
    has_api_key = False
    try:
        ws_id = _get_active_workspace_id()
        for provider in ["openai_key", "anthropic_key", "google_key"]:
            if get_key_local("local_user", provider):
                has_api_key = True
                break
    except Exception:
        pass

    # Step 2: At least one bot created?
    bot_count = conn.execute("SELECT COUNT(*) as cnt FROM bots").fetchone()["cnt"]
    has_bot = bot_count > 0

    # Step 3: At least one chat sent?
    chat_count = conn.execute("SELECT COUNT(*) as cnt FROM chat_histories").fetchone()["cnt"]
    has_chatted = chat_count > 0

    # Step 4: At least one flow created?
    flow_count = 0
    try:
        flow_count = conn.execute("SELECT COUNT(*) as cnt FROM flows").fetchone()["cnt"]
    except Exception:
        pass
    has_flow = flow_count > 0

    # Check if onboarding was dismissed
    dismissed_row = conn.execute("SELECT value FROM user_preferences WHERE key = 'onboarding_dismissed'").fetchone()
    dismissed = dismissed_row["value"] == "true" if dismissed_row else False

    steps = [
        {"id": "api_key", "label": "Add your API Key", "complete": has_api_key, "route": "Settings"},
        {"id": "create_bot", "label": "Create your first Bot", "complete": has_bot, "route": "Manage Bots"},
        {"id": "first_chat", "label": "Send your first message", "complete": has_chatted, "route": "Chat"},
        {"id": "create_flow", "label": "Create or try a Flow", "complete": has_flow, "route": "Automation Studio"},
    ]

    all_complete = all(s["complete"] for s in steps)

    return {
        "dismissed": dismissed,
        "all_complete": all_complete,
        "progress": sum(1 for s in steps if s["complete"]),
        "total": len(steps),
        "steps": steps
    }

@router.post("/onboarding/dismiss")
async def dismiss_onboarding():
    _ensure_table()
    conn = _get_connection()
    conn.execute("INSERT OR REPLACE INTO user_preferences (key, value) VALUES ('onboarding_dismissed', 'true')")
    conn.commit()
    return {"status": "dismissed"}
