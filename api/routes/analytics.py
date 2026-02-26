"""
Wolfclaw V3 — Usage Analytics API Routes (Phase 17)

Track token usage, cost, and performance across all LLM calls.
"""

import os
from fastapi import APIRouter, HTTPException
from core import local_db
from core.bot_manager import _get_active_workspace_id

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
async def get_usage_summary():
    """Get aggregate usage stats for the workspace."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Restricted to Desktop.")
    try:
        ws_id = _get_active_workspace_id()
        summary = local_db.get_usage_summary(ws_id)
        return {"status": "success", **summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-model")
async def get_usage_by_model():
    """Get usage breakdown by AI model."""
    try:
        ws_id = _get_active_workspace_id()
        data = local_db.get_usage_by_model(ws_id)
        return {"status": "success", "models": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-bot")
async def get_usage_by_bot():
    """Get usage breakdown by bot."""
    try:
        ws_id = _get_active_workspace_id()
        data = local_db.get_usage_by_bot(ws_id)
        
        # Enrich with bot names
        bot_dict = local_db.get_bots_for_workspace(ws_id)
        for item in data:
            bot_id = item['bot_id']
            if bot_id in bot_dict:
                item['bot_name'] = bot_dict[bot_id]['name']
            else:
                item['bot_name'] = 'Unknown Bot'
        
        return {"status": "success", "bots": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily")
async def get_daily_usage(days: int = 30):
    """Get daily usage for charting."""
    try:
        ws_id = _get_active_workspace_id()
        data = local_db.get_usage_daily(ws_id, days=days)
        return {"status": "success", "daily": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
