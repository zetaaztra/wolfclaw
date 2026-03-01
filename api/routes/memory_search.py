"""
Memory Search — search past chat conversations with keyword matching.
"""
from fastapi import APIRouter, Query
from core.local_db import _get_connection
import json

router = APIRouter()

@router.get("/memory/search")
async def search_memory(q: str = Query(..., min_length=1)):
    """Search all saved chat histories for a keyword or phrase."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT id, bot_id, title, messages, updated_at FROM chat_histories"
    ).fetchall()

    results = []
    query_lower = q.lower()
    for row in rows:
        try:
            messages = json.loads(row["messages"]) if row["messages"] else []
        except (json.JSONDecodeError, TypeError):
            continue

        matching_snippets = []
        for msg in messages:
            content = msg.get("content", "")
            if query_lower in content.lower():
                # Extract a snippet around the match
                idx = content.lower().index(query_lower)
                start = max(0, idx - 60)
                end = min(len(content), idx + len(q) + 60)
                snippet = ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")
                matching_snippets.append({
                    "role": msg.get("role", "unknown"),
                    "snippet": snippet
                })

        if matching_snippets:
            results.append({
                "chat_id": row["id"],
                "bot_id": row["bot_id"],
                "title": row["title"],
                "updated_at": row["updated_at"],
                "matches": matching_snippets[:5]  # Cap at 5 snippets per chat
            })

    return {"query": q, "result_count": len(results), "results": results}
