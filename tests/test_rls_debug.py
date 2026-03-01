"""
Direct end-to-end RLS debug test.
Tests the EXACT same code path that Streamlit Cloud uses.
"""
import os
from dotenv import load_dotenv
load_dotenv()

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_KEY"]

print(f"SUPABASE_URL: {url}")
print(f"SUPABASE_KEY: {key[:20]}... (len={len(key)})")

from supabase import create_client

# Step 1: Create unauthenticated client & login
print("\n--- STEP 1: Login ---")
login_client = create_client(url, key)

# Use the test account — user should provide real credentials
email = input("Enter your Supabase email: ").strip()
password = input("Enter your Supabase password: ").strip()

resp = login_client.auth.sign_in_with_password({"email": email, "password": password})
print(f"Login success: user.id = {resp.user.id}")
print(f"Session type: {type(resp.session).__name__}")

token = resp.session.access_token
refresh_token = resp.session.refresh_token
user_id = str(resp.user.id)

print(f"JWT token prefix: {token[:30]}...")
print(f"Refresh token prefix: {refresh_token[:20]}...")

# Step 2: Create a new client (simulating get_supabase())
print("\n--- STEP 2: Create data client & inject auth ---")
data_client = create_client(url, key)

print(f"PostgREST headers BEFORE auth: {dict(data_client.postgrest.session.headers).get('authorization', 'NOT SET')[:40]}")

# This is the key line — does postgrest.auth() actually change the header?
data_client.postgrest.auth(token)

print(f"PostgREST headers AFTER auth:  {dict(data_client.postgrest.session.headers).get('authorization', 'NOT SET')[:40]}")

# Step 3: Test the vault upsert
print("\n--- STEP 3: Test vault upsert ---")
try:
    data = {"user_id": user_id, "nvidia_key": "TEST_KEY_FROM_DEBUG"}
    result = data_client.table("vault").upsert(data, on_conflict="user_id").execute()
    print(f"✅ SUCCESS! Result: {result.data}")
except Exception as e:
    print(f"❌ FAILED: {e}")

# Step 4: Also test set_session approach
print("\n--- STEP 4: Test with set_session approach ---")
data_client2 = create_client(url, key)
try:
    data_client2.auth.set_session(token, refresh_token)
    result2 = data_client2.table("vault").upsert({"user_id": user_id, "nvidia_key": "TEST_KEY_2"}, on_conflict="user_id").execute()
    print(f"✅ set_session SUCCESS! Result: {result2.data}")
except Exception as e:
    print(f"❌ set_session FAILED: {e}")

# Step 5: Test with raw header injection
print("\n--- STEP 5: Test with direct session header injection ---")
data_client3 = create_client(url, key)
data_client3.postgrest.session.headers["authorization"] = f"Bearer {token}"
try:
    result3 = data_client3.table("vault").upsert({"user_id": user_id, "nvidia_key": "TEST_KEY_3"}, on_conflict="user_id").execute()
    print(f"✅ Direct header SUCCESS! Result: {result3.data}")
except Exception as e:
    print(f"❌ Direct header FAILED: {e}")

print("\n--- DONE ---")
