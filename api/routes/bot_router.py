"""
Phase 14 — Bot Router API Routes
Configure and use intent-based bot-to-bot routing.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from core.bot_router import bot_router
from core.local_db import get_bots_for_workspace
from core.bot_manager import _get_active_workspace_id

router = APIRouter()

class RouteRuleRequest(BaseModel):
    bot_id: str
    keywords: List[str]

class RouteMessageRequest(BaseModel):
    message: str

@router.post("/router/rules")
async def set_routing_rule(req: RouteRuleRequest):
    """Set custom routing keywords for a bot."""
    bot_router.set_rule(req.bot_id, req.keywords)
    return {"status": "rule_set", "bot_id": req.bot_id, "keywords": req.keywords}

@router.get("/router/rules")
async def get_routing_rules():
    return {"rules": bot_router.get_rules()}

@router.delete("/router/rules/{bot_id}")
async def delete_routing_rule(bot_id: str):
    bot_router.remove_rule(bot_id)
    return {"status": "rule_removed"}

@router.post("/router/route")
async def route_message(req: RouteMessageRequest):
    """Determine which bot should handle this message."""
    ws_id = _get_active_workspace_id()
    bots = get_bots_for_workspace(ws_id)
    if not bots:
        return {"error": "No bots available"}
    best_bot_id = bot_router.route(req.message, bots)
    bot_info = bots.get(best_bot_id, {})
    return {
        "routed_to": best_bot_id,
        "bot_name": bot_info.get("name", "Unknown"),
        "message": req.message
    }
