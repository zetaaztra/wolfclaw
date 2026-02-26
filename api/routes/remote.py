from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from core import local_db
from core.bot_manager import _get_active_workspace_id

router = APIRouter()

import uuid

class SSHConfigRequest(BaseModel):
    id: Optional[str] = None
    name: str = "My Server"
    host: str
    port: str = "22"
    user: str = "ubuntu"
    password: Optional[str] = ""
    key_content: Optional[str] = ""

class SSHTestRequest(BaseModel):
    host: str
    port: str = "22"
    user: str = "ubuntu"
    password: Optional[str] = ""
    key_content: Optional[str] = ""

@router.get("/servers")
async def get_ssh_servers():
    """Load all saved SSH configurations for the current workspace"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    try:
        workspace_id = _get_active_workspace_id()
        servers = local_db.get_workspace_ssh(workspace_id)
        
        safe_servers = []
        for s in servers:
            safe_servers.append({
                "id": s.get("id"),
                "name": s.get("name", "My Server"),
                "host": s.get("host", ""),
                "port": s.get("port", "22"),
                "user": s.get("user", "ubuntu"),
                "has_password": bool(s.get("password", "")),
                "has_key": bool(s.get("key_content", ""))
            })
        return {"status": "success", "servers": safe_servers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/servers")
async def save_ssh_server(req: SSHConfigRequest):
    """Save or update an SSH server configuration"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    try:
        workspace_id = _get_active_workspace_id()
        servers = local_db.get_workspace_ssh(workspace_id)
        
        server_id = req.id if req.id else str(uuid.uuid4())
        
        existing_idx = next((i for i, s in enumerate(servers) if s.get("id") == server_id), -1)
        
        ssh_data = {
            "id": server_id,
            "name": req.name,
            "host": req.host,
            "port": req.port,
            "user": req.user,
            "password": req.password or "",
            "key_content": req.key_content or ""
        }
        
        # Preserve old password/keys if not provided in update
        if existing_idx >= 0:
            if not req.password and servers[existing_idx].get("password"):
                ssh_data["password"] = servers[existing_idx]["password"]
            if not req.key_content and servers[existing_idx].get("key_content"):
                ssh_data["key_content"] = servers[existing_idx]["key_content"]
            servers[existing_idx] = ssh_data
        else:
            servers.append(ssh_data)
            
        local_db.update_workspace_ssh(workspace_id, servers)
        return {"status": "success", "message": "Server saved.", "id": server_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/servers/{server_id}")
async def delete_ssh_server(server_id: str):
    """Delete an SSH server configuration"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    try:
        workspace_id = _get_active_workspace_id()
        servers = local_db.get_workspace_ssh(workspace_id)
        
        new_servers = [s for s in servers if s.get("id") != server_id]
        local_db.update_workspace_ssh(workspace_id, new_servers)
        
        return {"status": "success", "message": "Server deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_ssh_connection(req: SSHTestRequest):
    """Test an SSH connection using paramiko"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    if not req.host:
        raise HTTPException(status_code=400, detail="Hostname is required.")
    
    try:
        import paramiko
        import io
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        port_int = int(req.port) if req.port.isdigit() else 22
        
        if req.key_content:
            key_io = io.StringIO(req.key_content)
            key = paramiko.RSAKey.from_private_key(key_io)
            client.connect(hostname=req.host, port=port_int, username=req.user, pkey=key, timeout=5)
        elif req.password:
            client.connect(hostname=req.host, port=port_int, username=req.user, password=req.password, timeout=5)
        else:
            raise HTTPException(status_code=400, detail="Provide a password or PEM key.")
        
        stdin, stdout, stderr = client.exec_command("hostname && uname -a && df -h --total | tail -1")
        output = stdout.read().decode('utf-8').strip()
        client.close()
        
        lines = output.split('\n')
        hostname = lines[0] if len(lines) > 0 else "unknown"
        system_info = lines[1] if len(lines) > 1 else ""
        disk_info = lines[2] if len(lines) > 2 else ""
        
        return {
            "status": "success", 
            "hostname": hostname,
            "system_info": system_info,
            "disk_info": disk_info,
            "message": f"Connected successfully to {hostname}!"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection failed: {e}")
