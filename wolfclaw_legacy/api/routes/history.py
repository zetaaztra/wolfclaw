from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import os

from core import local_db
from core.bot_manager import _get_active_workspace_id

router = APIRouter(prefix="/history", tags=["history"])

class SaveHistoryRequest(BaseModel):
    bot_id: str
    title: str
    messages: str  # JSON string of messages
    chat_id: Optional[str] = None

@router.get("/")
async def list_history():
    """List all chat histories for the active workspace."""
    ws_id = _get_active_workspace_id()
    try:
        histories = local_db.get_chat_histories(ws_id)
        return {"histories": histories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{chat_id}")
async def get_history(chat_id: str):
    """Get a specific chat history by ID."""
    try:
        history = local_db.get_chat_history(chat_id)
        if not history:
            raise HTTPException(status_code=404, detail="Chat history not found")
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def save_history(req: SaveHistoryRequest):
    """Save or update a chat history."""
    ws_id = _get_active_workspace_id()
    try:
        chat_id = local_db.save_chat_history(
            ws_id=ws_id,
            bot_id=req.bot_id,
            title=req.title,
            messages=req.messages,
            chat_id=req.chat_id
        )
        return {"status": "success", "chat_id": chat_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{chat_id}")
async def delete_history(chat_id: str):
    """Delete a chat history."""
    try:
        local_db.delete_chat_history(chat_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
