from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from core import local_db

router = APIRouter()

class DeleteRequest(BaseModel):
    user_id: str

@router.delete("/delete")
async def delete_account(req: DeleteRequest):
    """Local SQLite Account Deletion"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    try:
        local_db.delete_user(req.user_id)
        return {"status": "success", "message": "Account securely deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
