import os
from dotenv import load_dotenv

load_dotenv()

# Requires SUPABASE_URL and SUPABASE_KEY in .env or st.secrets
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def get_supabase_client():
    from supabase import create_client, Client
    if not SUPABASE_URL or not SUPABASE_KEY:
        try:
            import streamlit as st
            st.error("Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY.")
            st.stop()
        except Exception:
            raise RuntimeError("Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def login_user(email, password):
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        import hashlib
        
        user = local_db.get_user_by_email(email)
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if user and user["password_hash"] == pwd_hash:
            # Mock a user object structure expected by views.py
            class DummyUser: id = user["id"]
            class DummySession: access_token = "local_token"
            
            try:
                import streamlit as st
                st.session_state["user"] = DummyUser()
                st.session_state["session"] = DummySession()
            except:
                pass
            return True, None
        return False, "Invalid credentials"

    client = get_supabase_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            try:
                import streamlit as st
                st.session_state["user"] = response.user
                st.session_state["session"] = response.session
            except:
                pass
            return True, None
    except Exception as e:
        return False, str(e)
    return False, "Unknown error"

def signup_user(email, password):
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        import hashlib
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            local_db.create_user(email, pwd_hash)
            return True, "Account created successfully! You can now log in."
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Database error: {e}"

    client = get_supabase_client()
    try:
        response = client.auth.sign_up({"email": email, "password": password})
        if response.user:
            return True, "Check your email for verification!"
    except Exception as e:
        return False, str(e)
    return False, "Unknown error"

def logout_user():
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        client = get_supabase_client()
        try:
            client.auth.sign_out()
        except:
            pass
            
    try:
        import streamlit as st
        st.session_state["user"] = None
        st.session_state["session"] = None
    except:
        pass

def get_current_user():
    # 1. Try Streamlit session state first
    try:
        import streamlit as st
        user = st.session_state.get("user")
        if user: return user
    except:
        pass
    
    # 2. If no memory state, check persistent local_db session
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        from core import local_db
        conn = local_db._get_connection()
        row = conn.execute("SELECT user_id FROM sessions ORDER BY created_at DESC LIMIT 1").fetchone()
        conn.close()
        
        if row:
            user_data = local_db.get_user_by_id(row["user_id"])
            if user_data:
                class DummyUser: id = user_data["id"]; email = user_data["email"]
                return DummyUser()
    return None

def delete_account():
    """Wipes the user's data from Supabase public schemas. 
    (RLS policies ensure they can only delete their own data based on auth.uid())"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        return False, "This function is for Cloud. Use local_db.delete_user() instead."
        
    from core.config import get_supabase
    client = get_supabase()
    user = get_current_user()
    if not user:
        return False, "Not logged in."
        
    try:
        # A cascading delete on their vault will wipe everything properly configured
        client.table("vault").delete().eq("user_id", user.id).execute()
        # Workspaces and bots are linked directly or indirectly
        client.table("workspaces").delete().eq("user_id", user.id).execute()
        
        # After wiping data, sign them out
        logout_user()
        return True, "Account data effectively deleted."
    except Exception as e:
        return False, str(e)
