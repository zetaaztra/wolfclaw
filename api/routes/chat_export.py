"""
Phase 14 — Conversation Export API
Export chats as clean Markdown or plain-text files.
"""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from core.local_db import _get_connection

router = APIRouter()

@router.get("/chat/{chat_id}/export")
async def export_chat(chat_id: str, format: str = "markdown"):
    """Export a chat as Markdown or plain text."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT title, messages, updated_at, bot_id FROM chat_histories WHERE id = ?", (chat_id,)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Chat not found.")

    messages = json.loads(row["messages"]) if row["messages"] else []

    # Get bot name
    bot_name = "Unknown Bot"
    if row["bot_id"]:
        bot_row = conn.execute("SELECT name FROM bots WHERE id = ?", (row["bot_id"],)).fetchone()
        if bot_row:
            bot_name = bot_row["name"]

    if format == "markdown":
        content = _to_markdown(row["title"], bot_name, row["updated_at"], messages)
    else:
        content = _to_plain(row["title"], bot_name, row["updated_at"], messages)

    filename = (row["title"] or "chat_export").replace(" ", "_")[:50]
    ext = "md" if format == "markdown" else "txt"

    return PlainTextResponse(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}.{ext}"'}
    )


def _to_markdown(title: str, bot_name: str, date: str, messages: list) -> str:
    lines = [
        f"# {title or 'Chat Export'}",
        f"**Bot:** {bot_name}  ",
        f"**Date:** {date}  ",
        f"**Messages:** {len(messages)}",
        "",
        "---",
        ""
    ]
    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        if role == "USER":
            lines.append(f"### 🗣️ You")
        elif role == "ASSISTANT":
            lines.append(f"### 🤖 {bot_name}")
        else:
            lines.append(f"### {role}")
        lines.append(content)
        lines.append("")

    lines.append("---")
    lines.append("*Exported from Wolfclaw AI Command Center*")
    return "\n".join(lines)


def _to_plain(title: str, bot_name: str, date: str, messages: list) -> str:
    lines = [
        f"CHAT EXPORT: {title}",
        f"Bot: {bot_name}",
        f"Date: {date}",
        f"Messages: {len(messages)}",
        "=" * 50, ""
    ]
    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        lines.append(f"[{role}]:")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)
