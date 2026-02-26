from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from pydantic import BaseModel
import os
import shutil
from pathlib import Path
from core.config import set_key, get_key

router = APIRouter()

class SlackTokenRequest(BaseModel):
    token: str

@router.post("/slack")
async def save_slack_token(request: SlackTokenRequest):
    """Save the Slack Bot Token to env/config."""
    # For now, we update the process environment and could save to config
    os.environ["SLACK_BOT_TOKEN"] = request.token
    try:
        # Also persist to our key storage (assume standard set_key handles this)
        set_key("slack", request.token)
    except Exception:
        pass
    return {"status": "success", "message": "Slack token saved."}

@router.get("/slack")
async def get_slack_status():
    """Check if Slack is configured."""
    has_token = bool(os.environ.get("SLACK_BOT_TOKEN") or get_key("slack"))
    return {"configured": has_token}


@router.post("/google/upload_credentials")
async def upload_google_credentials(file: UploadFile = File(...)):
    """Upload google_credentials.json for Google Workspace Integration."""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are allowed.")
        
    core_integrations_dir = Path("core/integrations").resolve()
    core_integrations_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = core_integrations_dir / "google_credentials.json"
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"status": "success", "message": "Google credentials uploaded successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save credentials: {str(e)}")

@router.get("/google/status")
async def get_google_status():
    """Check if Google Workspace is configured and authenticated."""
    core_integrations_dir = Path("core/integrations").resolve()
    creds_path = core_integrations_dir / "google_credentials.json"
    token_path = core_integrations_dir / "google_token.json"
    
    return {
        "has_credentials": creds_path.exists(),
        "is_authenticated": token_path.exists()
    }
