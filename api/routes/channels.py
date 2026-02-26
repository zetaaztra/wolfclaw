from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import sys
import subprocess
import httpx
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks

from core import local_db, bot_manager
from core.bot_manager import _get_active_workspace_id
from core.config import get_current_user_id

router = APIRouter()

# In-memory store for running Telegram workers
_telegram_workers = {}

class TelegramSaveRequest(BaseModel):
    bot_id: str
    token: str

class TelegramStartRequest(BaseModel):
    bot_id: str

@router.post("/telegram/save")
async def save_telegram_token(req: TelegramSaveRequest):
    """Save a Telegram Bot token for a specific bot"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")

    try:
        local_db.update_bot_telegram(req.bot_id, req.token)
        return {"status": "success", "message": "Telegram token saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/unlink")
async def unlink_telegram_token(req: TelegramStartRequest):
    """Unlink a Telegram Bot token and stop any running worker"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")

    try:
        local_db.update_bot_telegram(req.bot_id, "")
        if req.bot_id in _telegram_workers:
            proc = _telegram_workers[req.bot_id]
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
            del _telegram_workers[req.bot_id]

        return {"status": "success", "message": "Telegram token unlinked."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/start")
async def start_telegram_worker(req: TelegramStartRequest):
    """Start a local Telegram polling worker for the specified bot"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")

    try:
        # Get bot data
        bots = bot_manager.get_bots()
        if req.bot_id not in bots:
            raise HTTPException(status_code=404, detail="Bot not found.")
        
        bot_data = bots[req.bot_id]
        tg_token = bot_data.get("telegram_token", "")
        if not tg_token:
            raise HTTPException(status_code=400, detail="No Telegram token saved for this bot.")
        
        # Kill ALL existing workers to prevent Telegram polling conflicts
        for old_id in list(_telegram_workers.keys()):
            old_proc = _telegram_workers[old_id]
            try:
                if old_proc.poll() is None:
                    old_proc.terminate()
            except Exception:
                pass
            del _telegram_workers[old_id]
        
        # Build env
        env = os.environ.copy()
        
        # Inject the active user's ID into the worker environment so it can fetch the correct API keys
        uid = get_current_user_id()
        env["WOLFCLAW_WEBHOOK_USER_ID"] = uid
        
        env["TELEGRAM_TOKEN"] = tg_token
        env["WOLFCLAW_MODEL"] = bot_data.get("model", "gpt-4o")
        env["WOLFCLAW_PROMPT"] = bot_data.get("prompt", "")
        env["WOLFCLAW_BOT_ID"] = req.bot_id
        env["WOLFCLAW_FALLBACKS"] = ",".join(bot_data.get("fallback_models", []))
        
        # Load SSH credentials into env for tool usage
        workspace_id = _get_active_workspace_id()
        ssh_data = local_db.get_workspace_ssh(workspace_id)
        env["WOLFCLAW_SSH_HOST"] = ssh_data.get("host", "")
        env["WOLFCLAW_SSH_PORT"] = str(ssh_data.get("port", "22"))
        env["WOLFCLAW_SSH_USER"] = ssh_data.get("user", "ubuntu")
        env["WOLFCLAW_SSH_PASSWORD"] = ssh_data.get("password", "")
        env["WOLFCLAW_SSH_KEY_CONTENT"] = ssh_data.get("key_content", "")
        
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "channels", "telegram_worker.py")
        
        # When running as a frozen .exe, sys.executable is the .exe itself,
        # NOT Python. Spawning it would open a duplicate app window.
        # Instead, run the telegram worker in-process as a daemon thread.
        if getattr(sys, 'frozen', False):
            import threading
            
            def _run_telegram_worker(env_vars):
                """Run telegram_worker.main() in a background thread with injected env."""
                for k, v in env_vars.items():
                    os.environ[k] = v
                try:
                    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from channels.telegram_worker import main as tg_main
                    tg_main()
                except Exception as e:
                    print(f"Telegram worker thread error: {e}")
            
            worker_env = {
                "WOLFCLAW_WEBHOOK_USER_ID": uid,
                "TELEGRAM_TOKEN": tg_token,
                "WOLFCLAW_MODEL": bot_data.get("model", "gpt-4o"),
                "WOLFCLAW_PROMPT": bot_data.get("prompt", ""),
                "WOLFCLAW_BOT_ID": req.bot_id,
                "WOLFCLAW_FALLBACKS": ",".join(bot_data.get("fallback_models", [])),
                "WOLFCLAW_SSH_HOST": ssh_data.get("host", ""),
                "WOLFCLAW_SSH_PORT": str(ssh_data.get("port", "22")),
                "WOLFCLAW_SSH_USER": ssh_data.get("user", "ubuntu"),
                "WOLFCLAW_SSH_PASSWORD": ssh_data.get("password", ""),
                "WOLFCLAW_SSH_KEY_CONTENT": ssh_data.get("key_content", ""),
            }
            
            t = threading.Thread(target=_run_telegram_worker, args=(worker_env,), daemon=True)
            t.start()
            
            # Store a mock process-like object for status tracking
            class _ThreadWorker:
                def __init__(self, thread):
                    self._thread = thread
                    self.pid = id(thread)
                def poll(self):
                    return None if self._thread.is_alive() else 0
                def terminate(self):
                    pass  # Threads can't be terminated — user must stop via UI
            
            _telegram_workers[req.bot_id] = _ThreadWorker(t)
            return {"status": "success", "pid": id(t), "message": f"Telegram worker started (in-process thread)."}
        else:
            # Running from source Python — safe to use subprocess
            proc = subprocess.Popen([sys.executable, script_path], env=env)
            _telegram_workers[req.bot_id] = proc
            return {"status": "success", "pid": proc.pid, "message": f"Telegram worker started (PID {proc.pid})."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/stop")
async def stop_telegram_worker(req: TelegramStartRequest):
    """Stop a running Telegram worker"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")

    if req.bot_id in _telegram_workers:
        proc = _telegram_workers[req.bot_id]
        if proc.poll() is None:
            proc.terminate()
        del _telegram_workers[req.bot_id]
        return {"status": "success", "message": "Worker stopped."}
    
    return {"status": "success", "message": "No worker was running."}

@router.get("/telegram/status")
async def telegram_status():
    """Get status of all Telegram workers"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")

    statuses = {}
    for bot_id, proc in list(_telegram_workers.items()):
        if proc.poll() is None:
            statuses[bot_id] = {"alive": True, "pid": proc.pid}
        else:
            statuses[bot_id] = {"alive": False, "pid": None}
            del _telegram_workers[bot_id]
    
    return {"status": "success", "workers": statuses}

@router.post("/telegram/webhook/{bot_id}")
async def telegram_webhook(bot_id: str, request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint to securely receive Telegram updates for Cloud Scaling.
    Requires FastAPI to be hosted externally from Streamlit Cloud.
    """
    try:
        update = await request.json()
    except Exception:
        return {"status": "invalid json"}

    if "message" not in update or "text" not in update["message"]:
        return {"status": "ignored"}
        
    text = update["message"]["text"]
    chat_id = update["message"]["chat"]["id"]
    sender_id = update["message"]["from"]["id"]
    
    from core.config import get_supabase
    try:
        # Note: If RLS is enabled, the FastAPI environment must have 
        # SUPABASE_SERVICE_ROLE_KEY set as SUPABASE_KEY to bypass RLS here.
        supabase = get_supabase()
        resp = supabase.table("bots").select("*").eq("id", bot_id).execute()
        if not resp.data:
            return {"status": "bot not found"}
            
        bot_data = resp.data[0]
        token = bot_data.get("telegram_token")
        if not token:
            return {"status": "no token configured"}
            
        background_tasks.add_task(_process_telegram_message, bot_id, bot_data, token, chat_id, text, sender_id)
        return {"status": "processing"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def _process_telegram_message(bot_id, bot_data, token, chat_id, text, sender_id):
    """Stateless worker that executes WolfEngine logic for incoming webhooks."""
    from core.llm_engine import WolfEngine
    try:
        # Load history manually or from DB in future
        messages = [{"role": "user", "content": text}]
        
        fallback_str = bot_data.get("fallback_models", "")
        if isinstance(fallback_str, str):
            fallbacks = [x.strip() for x in fallback_str.split(",") if x.strip()]
        else:
            fallbacks = fallback_str or []
            
        engine = WolfEngine(bot_data.get("model", "gpt-4o"), fallback_models=fallbacks)
        
        # Override the workspace ID and user ID manually in environment for this thread so tools can fetch SSH
        if getattr(bot_data, "workspace_id", None):
            os.environ["WOLFCLAW_WEBHOOK_WORKSPACE_ID"] = bot_data["workspace_id"]
        
        # In a real SaaS setup "user_id" would ideally be brought through bot relation. 
        # But we must safely query it if we need API keys from their vault.
        # Fallback to the owner env var if available
        owner_id = os.environ.get("WOLFCLAW_OWNER_ID")
        if owner_id:
             os.environ["WOLFCLAW_WEBHOOK_USER_ID"] = owner_id
            
        response = engine.chat(
            messages=messages, 
            system_prompt=bot_data.get("soul_prompt", ""),
            bot_id=bot_id
        )
        reply = response.choices[0].message.content
        
        if not reply or not reply.strip():
            reply = "*(Task completed)*"
            
        # Send reply back to Telegram
        async with httpx.AsyncClient() as client:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            await client.post(url, json={"chat_id": chat_id, "text": reply})
            
    except Exception as e:
        async with httpx.AsyncClient() as client:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            await client.post(url, json={"chat_id": chat_id, "text": f"Sorry, an error occurred in the AI engine: {e}"})
