import os
import sys
import logging
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
import httpx
from supabase import create_client, Client
from pydantic import BaseModel

# Add parent dir to path so we can import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.llm_engine import WolfEngine

# ── Logging Setup ──
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Wolfclaw Telegram Webhook")

# ── Supabase Setup ──
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    logger.warning("SUPABASE_URL or SUPABASE_KEY is missing. Database lookups will fail.")
    supabase = None

# Cache to avoid hitting Supabase for every single message
_bot_cache = {}

async def _send_telegram_message(token: str, chat_id: int, text: str):
    """Send text message via Telegram REST API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Try markdown first
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        # Fallback to plain text if markdown fails
        if resp.status_code != 200:
            payload["parse_mode"] = ""
            await client.post(url, json=payload)

async def _process_llm_chain(bot_id: str, bot_data: dict, chat_id: int, user_id: int, user_text: str):
    """The background task that actually talks to the LLM and executes tools."""
    token = bot_data.get("telegram_token")
    if not token:
        logger.error(f"Bot {bot_id} has no telegram token saved.")
        return

    # Security Check: Ensure the sender is the owner of the Workspace
    # (In a real app, you might map Telegram User IDs to Supabase Auth User IDs.
    # For now, we compare against WOLFCLAW_OWNER_ID or just allow it if they know the bot.)
    # In Phase 1/2 we didn't firmly map telegram ID to Supabase ID. Wait, if this is 
    # a SaaS, anyone chatting with the bot shouldn't be able to run SSH commands on 
    # the owner's server unless authorized!
    
    # For now, we will just pass the request to WolfEngine.
    engine = WolfEngine(bot_data.get("model", "gpt-4o"), fallback_models=bot_data.get("fallback_models", []))
    
    messages = [{"role": "user", "content": user_text}]
    
    try:
        # We need to explicitly inject the bot's SSH credentials before running the chat
        # so that run_remote_ssh_command works.
        try:
            ws_res = supabase.table("workspaces").select("ssh_config").eq("id", bot_data["workspace_id"]).execute()
            ssh_data = ws_res.data[0].get("ssh_config") or {}
            
            os.environ["WOLFCLAW_SSH_HOST"] = ssh_data.get("host", "")
            os.environ["WOLFCLAW_SSH_PORT"] = str(ssh_data.get("port", "22"))
            os.environ["WOLFCLAW_SSH_USER"] = ssh_data.get("user", "ubuntu")
            os.environ["WOLFCLAW_SSH_PASSWORD"] = ssh_data.get("password", "")
            os.environ["WOLFCLAW_SSH_KEY_CONTENT"] = ssh_data.get("key_content", "")
        except Exception as e:
            logger.warning(f"Failed to load SSH configs for bot {bot_id}: {e}")

        # Call the LLM
        response = engine.chat(
            messages=messages,
            system_prompt=bot_data.get("prompt", "You are a helpful AI."),
            bot_id=bot_id
        )
        reply = response.choices[0].message.content
        if not reply or not reply.strip():
            reply = "*(Action completed silently)*"
            
        await _send_telegram_message(token, chat_id, reply)
    except Exception as e:
        logger.error(f"Engine failure: {e}")
        await _send_telegram_message(token, chat_id, f"⚠️ Server Error: {str(e)}")


@app.post("/webhook/{bot_id}")
async def telegram_webhook(bot_id: str, request: Request, background_tasks: BackgroundTasks):
    """
    Receives incoming Telegram updates.
    The URL structure is: https://your-app.com/webhook/{bot_id}
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured.")
        
    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
        
    # Ignore anything that isn't a normal text message
    if "message" not in update or "text" not in update["message"]:
        return {"status": "ok", "ignored": True}
        
    chat_id = update["message"]["chat"]["id"]
    user_id = update["message"]["from"]["id"]
    text = update["message"]["text"]
    
    # 1. Look up the bot in Supabase using the bot_id from the URL
    if bot_id not in _bot_cache:
        try:
            res = supabase.table("bots").select("*").eq("id", bot_id).execute()
            if not res.data:
                raise HTTPException(status_code=404, detail="Bot not found")
            _bot_cache[bot_id] = res.data[0]
        except Exception as e:
            logger.error(f"Database error looking up bot {bot_id}: {e}")
            raise HTTPException(status_code=500, detail="Database error")
            
    bot_data = _bot_cache[bot_id]

    # 2. Enqueue the LLM processing in the background to return 200 OK immediately.
    # This prevents Telegram from retrying the Webhook if the LLM takes >10 seconds.
    background_tasks.add_task(_process_llm_chain, bot_id, bot_data, chat_id, user_id, text)
    
    return {"status": "ok"}

@app.get("/")
def health_check():
    return {"status": "Wolfclaw Webhook Server is running."}

# Useful for local testing with Uvicorn:
# uvicorn api.webhook:app --reload --port 8000
