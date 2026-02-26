from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os

from core import config
from api.deps import get_current_user

router = APIRouter()

class KeyRequest(BaseModel):
    provider: str
    key: str

@router.get("")
async def get_settings(user: dict = Depends(get_current_user)):
    """Retrieve all API keys for the current workspace (Local Desktop Mode only)"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    # We need to ensure config uses the correct user_id
    # Currently config.get_all_keys() uses get_current_user_id() which uses env vars.
    # We need to update config.py too or pass user_id.
        
    try:
        keys = config.get_all_keys(user_id=user["id"])
        return {"status": "success", "keys_set": keys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def save_setting(req: KeyRequest, user: dict = Depends(get_current_user)):
    """Save an API key securely"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    try:
        config.set_key(req.provider, req.key, user_id=user["id"])
        return {"status": "success", "message": f"{req.provider.capitalize()} key saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class KeyDeleteRequest(BaseModel):
    provider: str

@router.delete("")
async def delete_setting(req: KeyDeleteRequest, user: dict = Depends(get_current_user)):
    """Clear/delete a saved API key"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    try:
        config.set_key(req.provider, "", user_id=user["id"])
        return {"status": "success", "message": f"{req.provider.capitalize()} key cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

