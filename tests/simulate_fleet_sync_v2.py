import requests
import time
import json
import os

API_BASE = "http://127.0.0.1:8501/api"
WORKSPACE_ID = "default"  # Using default workspace for testing

import sqlite3
import time
def inject_mock_session():
    db_path = os.path.join(os.path.expanduser("~"), ".wolfclaw", "wolfclaw_local.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT OR IGNORE INTO users (id, email, password_hash) VALUES ('test_user', 'test@test.com', 'test')")
        conn.execute("DELETE FROM sessions WHERE session_id = 'local_dev_token'")
        conn.execute("INSERT INTO sessions (session_id, user_id, expires_at) VALUES ('local_dev_token', 'test_user', ?)", (int(time.time()) + 86400,))
        conn.execute("INSERT OR IGNORE INTO workspaces (id, user_id, name) VALUES ('default', 'test_user', 'Default')")
        conn.commit()
        print("[Auth] System injected mock session 'local_dev_token'")
    except Exception as e:
        print("[Auth] Warn: DB injection failed -", e)

inject_mock_session()

print("==================================================")
print("🐺 Wolfclaw Fleet Integrations & Sync Simulation")
print("==================================================")
print("Target: Native Desktop API (http://127.0.0.1:8501)")
print("Testing Modules: Wallet, Vault, Plugins, Macros, Flows")
print("--------------------------------------------------")

def test_endpoint(name, method, endpoint, data=None):
    url = f"{API_BASE}{endpoint}"
    print(f"\n[{name}] -> {method} {url}")
    try:
        headers = {"Authorization": "Bearer local_dev_token"}
        if method == "GET":
            res = requests.get(url, headers=headers, timeout=5)
        elif method == "POST":
            res = requests.post(url, json=data, headers=headers, timeout=10)
        
        status = res.status_code
        try:
            resp_data = res.json()
        except:
            resp_data = res.text[:200]
            
        print(f"Status: {status}")
        if status in [200, 201]:
            print(f"✅ SUCCESS")
            return resp_data
        else:
            print(f"❌ FAILED: {resp_data}")
            return None
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {e}")
        return None

# Wait a moment to ensure server is awake
time.sleep(1)

# 1. Test Wallet Integration
test_endpoint("Wallet Summary", "GET", "/wallet/summary/test_bot_123")

# 2. Test Vault (Secrets) Integration
test_endpoint("Secrets Vault List", "GET", "/vault")

# 3. Test Plugin Store Integration
test_endpoint("Marketplace Plugins", "GET", "/marketplace/plugins")

# 4. Test Macro Watch & Learn Integration
macro_res = test_endpoint("Macro Recording Start", "POST", "/macros/start")
if macro_res and macro_res.get("status") == "success":
    print("Recording started. Simulating 2 seconds of recording...")
    time.sleep(2)
    test_endpoint("Macro Recording Stop", "POST", "/macros/stop")
else:
    print("Skipping macro stop due to start failure.")

# 5. Test Magic Wand (Prompt to Flow) Integration
prompt_data = {"prompt": "Check my disk space and delete files in temp folder older than 30 days"}
test_endpoint("Magic Wand Flow Gen", "POST", "/flows/magic", data=prompt_data)

print("\n==================================================")
print("Simulation Complete.")
print("If all tests show ✅ SUCCESS, the fleet APIs are fully synced and operational.")
print("==================================================")
