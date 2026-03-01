"""
Phase 14 — Theme Engine API
Persist user theme preferences (dark/light + accent color).
"""
from fastapi import APIRouter
from pydantic import BaseModel
from core.local_db import _get_connection

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

class ThemeRequest(BaseModel):
    mode: str = "dark"  # dark or light
    accent: str = "#8b5cf6"  # purple default

@router.get("/theme")
async def get_theme():
    _ensure_table()
    conn = _get_connection()
    mode_row = conn.execute("SELECT value FROM user_preferences WHERE key = 'theme_mode'").fetchone()
    accent_row = conn.execute("SELECT value FROM user_preferences WHERE key = 'theme_accent'").fetchone()
    return {
        "mode": mode_row["value"] if mode_row else "dark",
        "accent": accent_row["value"] if accent_row else "#8b5cf6"
    }

@router.post("/theme")
async def set_theme(req: ThemeRequest):
    _ensure_table()
    conn = _get_connection()
    conn.execute("INSERT OR REPLACE INTO user_preferences (key, value) VALUES ('theme_mode', ?)", (req.mode,))
    conn.execute("INSERT OR REPLACE INTO user_preferences (key, value) VALUES ('theme_accent', ?)", (req.accent,))
    conn.commit()
    return {"status": "saved", "mode": req.mode, "accent": req.accent}
