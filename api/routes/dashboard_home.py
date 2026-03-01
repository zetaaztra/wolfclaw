"""
Phase 14 — Usage Dashboard API
Aggregated home screen data: today's stats, top bot, top flow, quick actions.
"""
from fastapi import APIRouter
from core.local_db import _get_connection
from core.bot_manager import _get_active_workspace_id
from datetime import datetime, date

router = APIRouter()

@router.get("/dashboard/home")
async def dashboard_home():
    """The Home Screen data — everything a user needs at a glance."""
    conn = _get_connection()
    today = date.today().isoformat()

    # --- Chats Today ---
    chats_today = conn.execute(
        "SELECT COUNT(*) as cnt FROM chat_histories WHERE date(updated_at) = ?", (today,)
    ).fetchone()["cnt"]

    # --- Total Chats Ever ---
    total_chats = conn.execute("SELECT COUNT(*) as cnt FROM chat_histories").fetchone()["cnt"]

    # --- Total Bots ---
    total_bots = conn.execute("SELECT COUNT(*) as cnt FROM bots").fetchone()["cnt"]

    # --- Total Flows ---
    total_flows = conn.execute("SELECT COUNT(*) as cnt FROM flows").fetchone()["cnt"]

    # --- Most Active Bot (most chats) ---
    top_bot_row = conn.execute(
        "SELECT bot_id, COUNT(*) as cnt FROM chat_histories GROUP BY bot_id ORDER BY cnt DESC LIMIT 1"
    ).fetchone()
    top_bot = None
    if top_bot_row:
        bot_info = conn.execute("SELECT name FROM bots WHERE id = ?", (top_bot_row["bot_id"],)).fetchone()
        top_bot = {"id": top_bot_row["bot_id"], "name": bot_info["name"] if bot_info else "Unknown", "chats": top_bot_row["cnt"]}

    # --- Token Usage (from usage_logs if available) ---
    tokens_today = 0
    cost_today = 0.0
    try:
        usage_row = conn.execute(
            "SELECT COALESCE(SUM(tokens_used), 0) as tokens, COALESCE(SUM(estimated_cost), 0) as cost FROM usage_logs WHERE date(created_at) = ?", (today,)
        ).fetchone()
        tokens_today = usage_row["tokens"]
        cost_today = round(usage_row["cost"], 4)
    except Exception:
        pass

    # --- 7-Day Sparkline Data ---
    sparkline = []
    try:
        rows = conn.execute(
            "SELECT date(updated_at) as day, COUNT(*) as cnt FROM chat_histories WHERE updated_at >= date('now', '-7 days') GROUP BY day ORDER BY day"
        ).fetchall()
        sparkline = [{"date": r["day"], "chats": r["cnt"]} for r in rows]
    except Exception:
        pass

    # --- Recent Activity (last 5) ---
    recent = []
    try:
        from core.activity_feed import activity_feed
        recent = activity_feed.get_recent(5)
    except Exception:
        pass

    return {
        "chats_today": chats_today,
        "total_chats": total_chats,
        "total_bots": total_bots,
        "total_flows": total_flows,
        "tokens_today": tokens_today,
        "cost_today": cost_today,
        "top_bot": top_bot,
        "sparkline_7d": sparkline,
        "recent_activity": recent,
        "timestamp": datetime.utcnow().isoformat()
    }
