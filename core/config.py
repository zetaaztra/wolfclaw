import os
from supabase import create_client, Client

def _get_st():
    """Lazy import streamlit — returns None if not available (e.g. inside .exe FastAPI)."""
    try:
        import streamlit as st
        return st
    except Exception:
        return None

def get_supabase() -> Client:
    """Initialize Supabase client with the logged-in user's auth token injected."""
    st = _get_st()
    
    # Read credentials from env vars OR Streamlit secrets
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    
    if not url or not key:
        try:
            if st:
                url = url or st.secrets["SUPABASE_URL"]
                key = key or st.secrets["SUPABASE_KEY"]
        except Exception:
            pass
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env or Streamlit Secrets")
    
    # ── CHECK: Use service role key if available (bypasses RLS entirely) ──
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not service_key:
        try:
            if st:
                service_key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
        except Exception:
            pass
    
    if service_key:
        # Service role key bypasses RLS — standard for server-side Supabase code
        return create_client(url, service_key)
    
    # ── FALLBACK: Try to inject user JWT into the anon key client ──
    token = None
    refresh_token = None
    if st:
        try:
            session = st.session_state.get("session")
            if session:
                token = getattr(session, "access_token", None)
                if not token and isinstance(session, dict):
                    token = session.get("access_token")
                refresh_token = getattr(session, "refresh_token", None)
                if not refresh_token and isinstance(session, dict):
                    refresh_token = session.get("refresh_token")
        except Exception:
            pass
    
    client = create_client(url, key)
    
    if token:
        # Method 1: postgrest.auth() — sets authorization header on the httpx session
        try:
            client.postgrest.auth(token)
        except Exception:
            pass
        
        # Method 2: Direct header injection on the httpx session (both cases)
        try:
            client.postgrest.session.headers["Authorization"] = f"Bearer {token}"
            client.postgrest.session.headers["authorization"] = f"Bearer {token}"
        except Exception:
            pass
        
        # Method 3: set_session on the GoTrue auth client
        if refresh_token:
            try:
                client.auth.set_session(token, refresh_token)
            except Exception:
                pass
    
    return client

def get_current_user_id() -> str:
    """Gets the active user ID from the Supabase session."""
    webhook_uid = os.environ.get("WOLFCLAW_WEBHOOK_USER_ID")
    if webhook_uid:
        return webhook_uid

    # Try fetching from Streamlit session state (UI users)
    try:
        import streamlit as st
        user = st.session_state.get("user")
        if user:
            uid = getattr(user, "id", None)
            if not uid and isinstance(user, dict):
                uid = user.get("id")
            if uid:
                return uid
    except:
        pass
    
    # Fallback to ENV variable (Telegram Bot Worker / API)
    return os.environ.get("WOLFCLAW_OWNER_ID", "00000000-0000-0000-0000-000000000000")

def set_key(provider: str, key: str, user_id: str = None):
    """Save an API key to the user's Vault (Supabase or Local DB)."""
    if not user_id:
        user_id = get_current_user_id()
    
    provider_lower = provider.lower()
    standard_map = {
        "openai": "openai_key",
        "anthropic": "anthropic_key",
        "nvidia": "nvidia_key",
        "google": "google_key",
        "deepseek": "deepseek_key"
    }
    
    col_name = standard_map.get(provider_lower, provider_lower)
        
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        local_db.set_key_local(user_id, col_name, key)
        return

    # If running in SaaS mode but without a real user ID, prevent Supabase RLS error
    if user_id == "00000000-0000-0000-0000-000000000000":
        raise PermissionError("Authentication required to save API keys in Cloud mode.")

    # Upsert the key into the vault for the current user
    supabase = get_supabase()
    
    # === DIAGNOSTIC DEBUG OUTPUT ===
    st = _get_st()
    if st:
        session = st.session_state.get("session")
        token = None
        if session:
            token = getattr(session, "access_token", None)
            if not token and isinstance(session, dict):
                token = session.get("access_token")
        
        # Show diagnostics in an expander so it doesn't clutter the UI
        with st.expander("🔍 Debug: Auth Diagnostics", expanded=True):
            st.write(f"**user_id:** `{user_id}`")
            st.write(f"**session type:** `{type(session).__name__}`")
            st.write(f"**token exists:** `{bool(token)}`")
            if token:
                st.write(f"**token prefix:** `{token[:20]}...`")
            else:
                st.error("❌ NO JWT TOKEN FOUND — this is why RLS fails!")
            
            # Check what headers PostgREST actually has
            try:
                pg_headers = dict(supabase.postgrest.session.headers)
                auth_h = pg_headers.get("Authorization", pg_headers.get("authorization", "NOT SET"))
                st.write(f"**PostgREST Auth header:** `{str(auth_h)[:40]}...`")
                st.write(f"**All PostgREST headers:** `{list(pg_headers.keys())}`")
            except Exception as ex:
                st.write(f"**PostgREST header check failed:** `{ex}`")
    # === END DIAGNOSTIC ===
    
    try:
        if col_name in standard_map.values():
            data = {"user_id": user_id, col_name: key}
            supabase.table("vault").upsert(data, on_conflict="user_id").execute()
        else:
            # Fetch existing dynamic keys
            res = supabase.table("vault").select("dynamic_keys").eq("user_id", user_id).execute()
            dyn = {}
            if res.data and len(res.data) > 0 and res.data[0].get("dynamic_keys"):
                import json
                try:
                    dyn = json.loads(res.data[0]["dynamic_keys"])
                except:
                    pass
            if key:
                dyn[col_name] = key
            elif col_name in dyn:
                del dyn[col_name]
            import json
            data = {"user_id": user_id, "dynamic_keys": json.dumps(dyn)}
            supabase.table("vault").upsert(data, on_conflict="user_id").execute()
    except Exception as e:
        raise Exception(f"Failed to save key: {e}")

def get_key(provider: str, user_id: str = None) -> str:
    """Retrieve an API key from the user's Vault (Supabase or Local DB)."""
    if not user_id:
        user_id = get_current_user_id()
    
    provider_lower = provider.lower()
    standard_map = {
        "openai": "openai_key",
        "anthropic": "anthropic_key",
        "nvidia": "nvidia_key",
        "google": "google_key",
        "deepseek": "deepseek_key"
    }
    
    col_name = standard_map.get(provider_lower, provider_lower)
        
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        return local_db.get_key_local(user_id, col_name)

    try:
        supabase = get_supabase()
        if col_name in standard_map.values():
            response = supabase.table("vault").select(col_name).eq("user_id", user_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0].get(col_name) or ""
        else:
            response = supabase.table("vault").select("dynamic_keys").eq("user_id", user_id).execute()
            if response.data and len(response.data) > 0 and response.data[0].get("dynamic_keys"):
                import json
                try:
                    dyn = json.loads(response.data[0]["dynamic_keys"])
                    return dyn.get(col_name) or ""
                except:
                    pass
        return ""
    except Exception:
        return ""

def get_all_keys(user_id: str = None) -> dict:
    """Retrieve all saved API keys (booleans of presence) for the user."""
    if not user_id:
        user_id = get_current_user_id()
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        return local_db.get_all_keys_local(user_id)
        
    try:
        supabase = get_supabase()
        response = supabase.table("vault").select("*").eq("user_id", user_id).execute()
        if not response.data:
            return {}
            
        row = response.data[0]
        keys = {}
        # Standard
        for k in ["openai_key", "anthropic_key", "nvidia_key", "google_key", "deepseek_key"]:
            if row.get(k):
                keys[k.replace("_key", "")] = True
                
        # Dynamic
        if row.get("dynamic_keys"):
            import json
            try:
                dyn = json.loads(row["dynamic_keys"])
                for dk, dv in dyn.items():
                    if dv:
                        keys[dk] = True
            except:
                pass
        return keys
    except Exception:
        return {}
