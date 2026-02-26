import os
import json
from datetime import datetime
from core.config import get_supabase, get_current_user_id

DEFAULT_USER_MD = """# USER PROFILE
## Personal Info
Name: [Your Name]
Location: [City, Country]
Timezone: [Your Timezone]

## Professional Info
Current Role: [Your role or 'Seeking']
Skills: [e.g., Python, JavaScript, Linux]
Target Roles: [e.g., Software Engineer, DevOps]

## Preferences
- Preferred language: English
- For code: explain after writing
- For long responses: bullet summary first
"""

DEFAULT_MEMORY_MD = """# LONG-TERM MEMORY
*This file is automatically updated by the AI after conversations.*
*It remembers important facts, preferences, and task history.*

## Facts Learned
- (none yet)

## Task History
- (none yet)
"""

def _get_active_workspace_id(user_id: str = None) -> str:
    """Gets the user's active workspace ID. Creates one if none exists."""
    webhook_ws = os.environ.get("WOLFCLAW_WEBHOOK_WORKSPACE_ID")
    if webhook_ws:
        print(f"[WORKSPACE] Using webhook override WorkspaceID: {webhook_ws}")
        return webhook_ws
        
    if not user_id:
        user_id = get_current_user_id()
    
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        print(f"[WORKSPACE] Fetching workspaces for UserID: {user_id} (Desktop)")
        workspaces = local_db.get_workspaces_for_user(user_id)
        if workspaces:
            ws_id = workspaces[0]["id"]
            print(f"[WORKSPACE] Found existing workspace: {ws_id}")
            return ws_id
            
        ws_id = local_db.create_workspace(user_id, "Default Workspace")
        print(f"[WORKSPACE] Created new default workspace: {ws_id}")
        return ws_id
    
    # If using SaaS mode but not authenticated, return a dummy workspace to prevent RLS crash
    if user_id == "00000000-0000-0000-0000-000000000000":
        print("[WORKSPACE] SaaS Mode: Authentication missing. Using DummyID.")
        return "00000000-0000-0000-0000-000000000000"

    supabase = get_supabase()
    # Check if a workspace exists
    try:
        print(f"[WORKSPACE] Fetching workspaces for UserID: {user_id} (Supabase)")
        resp = supabase.table("workspaces").select("id").eq("user_id", user_id).execute()
        if resp.data and len(resp.data) > 0:
            ws_id = resp.data[0]["id"]
            print(f"[WORKSPACE] Found Supabase workspace: {ws_id}")
            return ws_id
            
        # Create default workspace
        print(f"[WORKSPACE] Workspace not found. Creating default for UserID: {user_id}")
        insert_resp = supabase.table("workspaces").insert({"user_id": user_id, "name": "Default Workspace"}).execute()
        if insert_resp.data:
            ws_id = insert_resp.data[0]["id"]
            print(f"[WORKSPACE] Created Supabase workspace: {ws_id}")
            return ws_id
    except Exception as e:
        print(f"[WORKSPACE] ERROR fetching workspace: {e}")
        return "00000000-0000-0000-0000-000000000000"
    
    return "00000000-0000-0000-0000-000000000000"

def save_bot(bot_id: str, name: str, model: str, prompt: str, fallback_models: list = None, user_id: str = None):
    """Save a bot profile to Supabase or Local DB."""
    workspace_id = _get_active_workspace_id(user_id)
    
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        local_db.create_bot(workspace_id, name, model, prompt, fallback_models, bot_id=bot_id)
        return

    if workspace_id == "00000000-0000-0000-0000-000000000000":
        raise PermissionError("Authentication required to create bots in Cloud mode.")

    try:
        supabase = get_supabase()
        data = {
            "workspace_id": workspace_id,
            "name": name,
            "model": "gpt-4o" if model == "OpenAI: gpt-4o" else "meta/llama-3.1-70b-instruct",
            "soul_prompt": prompt,
            "user_context": DEFAULT_USER_MD,
            "memory": DEFAULT_MEMORY_MD
        }
        supabase.table("bots").insert(data).execute()
    except Exception as e:
        raise Exception(f"Failed to save bot: {e}")

def get_bots(user_id: str = None):
    """Retrieve all saved bots for the current workspace."""
    try:
        workspace_id = _get_active_workspace_id(user_id)
        
        if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
            from core import local_db
            local_bots = local_db.get_bots_for_workspace(workspace_id)
            for b_id, b_data in local_bots.items():
                b_data["status"] = "stopped"
                b_data["pid"] = None
                b_data["created_at"] = ""
            return local_bots

        supabase = get_supabase()
        resp = supabase.table("bots").select("*").eq("workspace_id", workspace_id).execute()
        
        bots_dict = {}
        if resp.data:
            for bot in resp.data:
                b_id = str(bot["id"])
                bots_dict[b_id] = {
                    "name": bot["name"],
                    "model": bot["model"],
                    "prompt": bot["soul_prompt"],
                    "status": "stopped",
                    "pid": None,
                    "telegram_token": bot.get("telegram_token", ""),
                    "created_at": bot["created_at"]
                }
        return bots_dict
    except Exception as e:
        print(f"Error fetching bots: {e}")
        return {}

def update_bot_status(bot_id: str, status: str, pid: int = None):
    """Transient method (not saved to DB in Phase 1 to save API calls)"""
    pass

def save_bot_token(bot_id: str, token: str):
    """Save the Telegram token."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        local_db.update_bot_telegram(bot_id, token)
        return

def read_workspace_file(bot_id: str, filename: str, user_id: str = None) -> str:
    """Read a file from a bot's Supabase profile or Local DB."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        workspace_id = _get_active_workspace_id(user_id)
        bots = local_db.get_bots_for_workspace(workspace_id)
        bot = bots.get(bot_id)
        if bot:
            if filename == "SOUL.md": return bot.get("prompt", "")
            if filename == "USER.md": return bot.get("user_context", "")
            if filename == "MEMORY.md": return bot.get("memory", "")
        return ""

    supabase = get_supabase()
    try:
        resp = supabase.table("bots").select("soul_prompt, user_context, memory").eq("id", bot_id).execute()
        if resp.data and len(resp.data) > 0:
            bot = resp.data[0]
            if filename == "SOUL.md": return bot.get("soul_prompt", "")
            if filename == "USER.md": return bot.get("user_context", "")
            if filename == "MEMORY.md": return bot.get("memory", "")
    except:
        pass
    return ""

def write_workspace_file(bot_id: str, filename: str, content: str, user_id: str = None):
    """Write content to a file in a bot's Supabase profile or Local DB."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        if filename == "SOUL.md": 
            local_db.update_bot_prompt(bot_id, content)
        elif filename == "USER.md":
            local_db.update_bot_user_context(bot_id, content)
        elif filename == "MEMORY.md":
            local_db.update_bot_memory(bot_id, content)
        return

    supabase = get_supabase()
    update_data = {}
    if filename == "SOUL.md": update_data["soul_prompt"] = content
    elif filename == "USER.md": update_data["user_context"] = content
    elif filename == "MEMORY.md": update_data["memory"] = content
    else: return
    
    try:
        supabase.table("bots").update(update_data).eq("id", bot_id).execute()
    except Exception as e:
        print(f"Error saving {filename} to Supabase: {e}")

def load_chat_history(bot_id: str) -> list:
    """Load persisted chat history for a bot from Supabase."""
    supabase = get_supabase()
    # In Phase 1, we map history.json to the chat_history table (if created)
    # Since we didn't add chat_history to the schema yet, we return empty to prevent crashes
    print("load_chat_history: Pending Chat History Table Migration")
    return []

def save_chat_history(bot_id: str, messages: list):
    """Persist chat history for a bot to Supabase."""
    print("save_chat_history: Pending Chat History Table Migration")

def delete_bot(bot_id: str, user_id: str = None):
    """Delete a bot from the registry."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        local_db.delete_bot(bot_id)
        return

    supabase = get_supabase()
    try:
        supabase.table("bots").delete().eq("id", bot_id).execute()
    except:
        pass
