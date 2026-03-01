from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
from core import wallet
from core import local_db
from core.bot_manager import _get_active_workspace_id

router = APIRouter()

class SetupWalletRequest(BaseModel):
    bot_id: str
    daily_budget: float

@router.get("/summary/{bot_id}")
async def get_wallet_info(bot_id: str):
    """Get the wallet summary for a specific bot."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    try:
        summary = wallet.get_wallet_summary(bot_id)
        return {"status": "success", "wallet": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/setup")
async def setup_wallet(req: SetupWalletRequest):
    """Set the daily budget for a specific bot."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    try:
        wallet.set_daily_budget(req.bot_id, req.daily_budget)
        return {"status": "success", "message": f"Daily budget set to ${req.daily_budget:.2f}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
