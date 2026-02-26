from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import uuid

# Using the existing local core managers
from core import bot_manager
from core.bot_manager import _get_active_workspace_id, DEFAULT_MEMORY_MD

router = APIRouter()

class BotProfile(BaseModel):
    name: str
    model: str
    prompt: str
    fallback_models: Optional[List[str]] = None

class ProfileUpdateRequest(BaseModel):
    filename: str  # "SOUL.md" or "USER.md"
    content: str

@router.get("/")
async def list_bots():
    """List all bots in the workspace (Local Desktop Mode only)"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    try:
        bots = bot_manager.get_bots()
        return {"status": "success", "bots": bots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_bot(bot: BotProfile):
    """Create a new bot profile"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    try:
        new_id = str(uuid.uuid4())
        bot_manager.save_bot(
            new_id, 
            bot.name, 
            bot.model, 
            bot.prompt, 
            fallback_models=bot.fallback_models
        )
        return {"status": "success", "bot_id": new_id, "message": "Bot created."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{bot_id}")
async def delete_bot(bot_id: str):
    """Delete a bot profile from the workspace"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    try:
        bot_manager.delete_bot(bot_id)
        return {"status": "success", "message": "Bot deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{bot_id}/profile")
async def get_bot_profile(bot_id: str):
    """Get SOUL.md, USER.md, MEMORY.md for a bot"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    try:
        soul = bot_manager.read_workspace_file(bot_id, "SOUL.md")
        user = bot_manager.read_workspace_file(bot_id, "USER.md")
        memory = bot_manager.read_workspace_file(bot_id, "MEMORY.md")
        return {
            "status": "success",
            "soul": soul,
            "user": user,
            "memory": memory
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{bot_id}/profile")
async def update_bot_profile(bot_id: str, req: ProfileUpdateRequest):
    """Update SOUL.md or USER.md for a bot"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    if req.filename not in ["SOUL.md", "USER.md"]:
        raise HTTPException(status_code=400, detail="Only SOUL.md and USER.md can be edited.")
    
    try:
        bot_manager.write_workspace_file(bot_id, req.filename, req.content)
        return {"status": "success", "message": f"{req.filename} saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{bot_id}/memory")
async def clear_bot_memory(bot_id: str):
    """Clear MEMORY.md to default"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    try:
        bot_manager.write_workspace_file(bot_id, "MEMORY.md", DEFAULT_MEMORY_MD)
        return {"status": "success", "message": "Memory cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

