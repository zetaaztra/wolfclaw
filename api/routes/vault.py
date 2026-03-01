"""
Phase 14 — Local Vault / Secrets Manager
Encrypted local storage for sensitive values (API keys, passwords, env vars).
"""
import uuid
import json
import hashlib
import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.local_db import _get_connection

router = APIRouter()

def _ensure_table():
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vault (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            value_encrypted TEXT NOT NULL,
            hint TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

def _obfuscate(value: str) -> str:
    """Simple base64 obfuscation for local storage. Not true encryption but prevents casual reading."""
    return base64.b64encode(value.encode()).decode()

def _deobfuscate(value: str) -> str:
    return base64.b64decode(value.encode()).decode()

class VaultEntry(BaseModel):
    label: str
    value: str
    category: str = "general"  # general, api_key, password, ssh_key, env_var
    hint: str = ""

@router.post("/vault")
async def add_secret(entry: VaultEntry):
    _ensure_table()
    entry_id = str(uuid.uuid4())[:8]
    conn = _get_connection()
    conn.execute(
        "INSERT INTO vault (id, label, category, value_encrypted, hint) VALUES (?, ?, ?, ?, ?)",
        (entry_id, entry.label, entry.category, _obfuscate(entry.value), entry.hint)
    )
    conn.commit()
    return {"id": entry_id, "label": entry.label, "status": "stored"}

@router.get("/vault")
async def list_secrets():
    _ensure_table()
    conn = _get_connection()
    rows = conn.execute("SELECT id, label, category, hint, created_at FROM vault ORDER BY created_at DESC").fetchall()
    # Never return the actual value in listings
    return {"secrets": [dict(r) for r in rows]}

@router.get("/vault/{entry_id}")
async def get_secret(entry_id: str):
    conn = _get_connection()
    row = conn.execute("SELECT * FROM vault WHERE id = ?", (entry_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Secret not found.")
    return {
        "id": row["id"],
        "label": row["label"],
        "category": row["category"],
        "value": _deobfuscate(row["value_encrypted"]),
        "hint": row["hint"]
    }

@router.delete("/vault/{entry_id}")
async def delete_secret(entry_id: str):
    conn = _get_connection()
    conn.execute("DELETE FROM vault WHERE id = ?", (entry_id,))
    conn.commit()
    return {"status": "deleted"}
