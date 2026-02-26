import os
import streamlit as st
from auth.supabase_client import login_user, get_supabase_client
from core.config import get_supabase

# Mock Streamlit session state
if "session_state" not in dir(st):
    st.session_state = {}

# Test Credentials - We need to enter valid credentials to test this. 
# Alternatively, we can just print the type of session.
print("Running test...")
