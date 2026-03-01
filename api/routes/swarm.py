from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
from auth.supabase_client import get_current_user
from core.swarm import swarm

router = APIRouter()

class SwarmRequest(BaseModel):
    task: str
    manager_bot_id: str
    worker_bot_ids: List[str]

@router.post("/execute")
async def execute_swarm(req: SwarmRequest):
    user = get_current_user()
    ws_id = user["id"] if user else "local_workspace"
    
    if not req.task or not req.manager_bot_id or not req.worker_bot_ids:
        raise HTTPException(status_code=400, detail="Missing required swarm parameters.")
        
    try:
        result = swarm.run_swarm(
            task=req.task,
            manager_bot_id=req.manager_bot_id,
            worker_bot_ids=req.worker_bot_ids,
            workspace_id=ws_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
