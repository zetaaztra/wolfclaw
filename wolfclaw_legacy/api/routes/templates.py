"""
Wolfclaw V3 — Template Gallery API Routes
Serves the template gallery and deploys templates as new bots.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.templates import get_all_templates, get_template_by_id
from core import local_db
from core.bot_manager import _get_active_workspace_id
import os

router = APIRouter(prefix="/templates", tags=["templates"])


class DeployTemplateRequest(BaseModel):
    template_id: str
    override_model: Optional[str] = None


@router.get("/")
async def list_templates():
    """Return all available profession templates and categories."""
    return get_all_templates()


@router.post("/deploy")
async def deploy_template(req: DeployTemplateRequest):
    """Deploy a template as a new bot — one-click creation."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")

    template = get_template_by_id(req.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")

    try:
        ws_id = _get_active_workspace_id()

        # Create the bot using existing infrastructure
        final_model = req.override_model if req.override_model else template["model"]
        bot_id = local_db.create_bot(
            ws_id=ws_id,
            name=template["name"],
            model=final_model,
            prompt=template["soul"]
        )

        return {
            "status": "success",
            "bot_id": bot_id,
            "name": template["name"],
            "message": f"✅ {template['name']} is ready! Start chatting now."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
