from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict
import os
from core import local_db
from core.config import get_current_user_id

router = APIRouter(prefix="/favorites", tags=["favorites"])

class SaveFavoriteRequest(BaseModel):
    bot_name: str
    content: str

@router.post("/")
async def save_favorite(req: SaveFavoriteRequest):
    """Save an AI response to favorites."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Favorites are currently a Desktop-only feature.")
        
    user_id = get_current_user_id()
    if not user_id or user_id == "00000000-0000-0000-0000-000000000000":
        user_id = "default_user_123" # Fallback for local testing without auth

    try:
        fav_id = local_db.save_favorite(user_id, req.bot_name, req.content)
        return {"status": "success", "id": fav_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_favorites():
    """Get all favorited responses for the current user."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Favorites are currently a Desktop-only feature.")
        
    user_id = get_current_user_id()
    if not user_id or user_id == "00000000-0000-0000-0000-000000000000":
        user_id = "default_user_123"

    try:
        favorites = local_db.get_favorites_for_user(user_id)
        return {"favorites": favorites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{fav_id}")
async def delete_favorite(fav_id: str):
    """Delete a favorited response."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Favorites are currently a Desktop-only feature.")
        
    try:
        local_db.delete_favorite(fav_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
