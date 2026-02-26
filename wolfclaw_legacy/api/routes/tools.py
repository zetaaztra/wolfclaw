"""Direct Tool Execution API — Run Wolfclaw tools from the GUI without the LLM."""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}


@router.post("/execute")
async def execute_tool_direct(req: ToolRequest):
    """Execute a single tool by name, returning the result."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Tool execution restricted to Desktop environment.")

    try:
        from core.tools import execute_tool
        result = execute_tool(req.tool_name, req.arguments)
        return {"status": "success", "tool": req.tool_name, "result": str(result)}
    except Exception as e:
        return {"status": "error", "tool": req.tool_name, "result": str(e)}
