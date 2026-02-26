import streamlit as st
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Ensure wolfclaw module path is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.views import login_view, dashboard_view

st.set_page_config(page_title="Wolfclaw", layout="centered")

def main():
    try:
        url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")
        if not url or not key:
            st.error("⚠️ **Missing Supabase Credentials!**\n\nThis app is running in Cloud Mode. Please configure `SUPABASE_URL` and `SUPABASE_KEY` in your Streamlit Secrets.")
            st.stop()
    except Exception:
        st.error("⚠️ **Streamlit Secrets not configured!**\n\nPlease add your Supabase credentials to the Streamlit Secret Manager to proceed.")
        st.stop()
        
    from auth.supabase_client import get_current_user
    user = get_current_user()
    
    if user is None:
        login_view()
    else:
        dashboard_view()

if __name__ == "__main__":
    main()
