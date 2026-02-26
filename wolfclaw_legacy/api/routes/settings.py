from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

from core import config

router = APIRouter()

class KeyRequest(BaseModel):
    provider: str
    key: str

@router.get("/")
async def get_settings():
    """Retrieve all API keys for the current workspace (Local Desktop Mode only)"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    try:
        keys = {
            "openai": config.get_key("openai") != "",
            "anthropic": config.get_key("anthropic") != "",
            "nvidia": config.get_key("nvidia") != "",
            "google": config.get_key("google") != "",
            "deepseek": config.get_key("deepseek") != "",
        }
        return {"status": "success", "keys_set": keys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def save_setting(req: KeyRequest):
    """Save an API key securely"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    try:
        config.set_key(req.provider, req.key)
        return {"status": "success", "message": f"{req.provider.capitalize()} key saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class KeyDeleteRequest(BaseModel):
    provider: str

@router.delete("/")
async def delete_setting(req: KeyDeleteRequest):
    """Clear/delete a saved API key"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    try:
        config.set_key(req.provider, "")
        return {"status": "success", "message": f"{req.provider.capitalize()} key cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

