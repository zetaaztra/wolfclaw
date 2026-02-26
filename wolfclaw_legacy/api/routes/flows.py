"""
API routes for Wolfclaw Flows — Visual Workflow Builder (Phase 27)
"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core import local_db
from core.bot_manager import _get_active_workspace_id
from core.flow_engine import FlowEngine, BLOCK_CATALOG

router = APIRouter()


class FlowCreate(BaseModel):
    name: str
    description: str = ""
    flow_data: str = "{}"  # JSON string of nodes + edges


class FlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    flow_data: Optional[str] = None


# ─────────── BLOCK CATALOG ───────────

@router.get("/flows/blocks")
async def get_block_catalog():
    """Return the available block types for the flow builder palette."""
    return {"blocks": BLOCK_CATALOG}


# ─────────── FLOW CRUD ───────────

@router.get("/flows")
async def list_flows():
    """List all flows for the current workspace."""
    ws_id = _get_active_workspace_id()
    flows = local_db.get_flows_for_workspace(ws_id)
    return {"flows": flows}


@router.post("/flows")
async def create_flow(body: FlowCreate):
    """Create a new flow."""
    ws_id = _get_active_workspace_id()
    
    # Validate flow_data is valid JSON
    try:
        json.loads(body.flow_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="flow_data must be valid JSON")
    
    flow_id = local_db.save_flow(ws_id, body.name, body.description, body.flow_data)
    return {"id": flow_id, "message": "Flow created"}


@router.get("/flows/{flow_id}")
async def get_flow(flow_id: str):
    """Get a single flow with full data."""
    flow = local_db.get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow


@router.put("/flows/{flow_id}")
async def update_flow(flow_id: str, body: FlowUpdate):
    """Update a flow."""
    existing = local_db.get_flow(flow_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    name = body.name or existing["name"]
    description = body.description if body.description is not None else existing["description"]
    flow_data = body.flow_data or existing["flow_data"]
    
    if body.flow_data:
        try:
            json.loads(body.flow_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="flow_data must be valid JSON")
    
    local_db.save_flow(
        ws_id=existing["workspace_id"],
        name=name,
        description=description,
        flow_data=flow_data,
        flow_id=flow_id
    )
    return {"message": "Flow updated"}


@router.delete("/flows/{flow_id}")
async def delete_flow(flow_id: str):
    """Delete a flow."""
    existing = local_db.get_flow(flow_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    local_db.delete_flow(flow_id)
    return {"message": "Flow deleted"}


# ─────────── FLOW EXECUTION ───────────

@router.post("/flows/{flow_id}/run")
async def run_flow(flow_id: str):
    """Execute a flow and return the results."""
    flow = local_db.get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    try:
        flow_data = json.loads(flow["flow_data"])
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid flow data")
    
    if not flow_data.get("nodes"):
        raise HTTPException(status_code=400, detail="Flow has no nodes to execute")
    
    engine = FlowEngine(flow_data)
    result = engine.execute()
    
    return result
