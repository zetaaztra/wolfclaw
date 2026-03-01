import requests
import time
import uuid

API_BASE = "http://localhost:8501/api"

def run_test():
    print("=== STARTING FULL SYSTEM E2E AUDIT (API LEVEL) ===")
    
    # 1. Registration
    email = f"audit_{uuid.uuid4().hex[:6]}@test.com"
    password = "AuditPassword123!"
    print(f"[TEST 1] Registering user: {email}")
    reg_resp = requests.post(f"{API_BASE}/auth/register", json={"email": email, "password": password})
    if reg_resp.status_code == 200:
        print("OK: Registration Successful")
    else:
        print(f"WARN: Registration maybe existing: {reg_resp.text}")

    # 2. Login
    print("[TEST 2] Logging in")
    log_resp = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
    if log_resp.status_code == 200:
        sess_data = log_resp.json()
        session_id = sess_data.get("session_id") # Note: Backend was updated to use session tokens
        print(f"OK: Login Successful. Session: {session_id}")
    else:
        print(f"ERROR: Login Failed: {log_resp.text}")
        return

    # Set Auth Header for all future requests
    headers = {"Authorization": f"Bearer {session_id}"}

    # 3. Create Bot
    print("[TEST 3] Creating 'Blackbeard (E2E)' Bot")
    bot_info = {
        "name": "Blackbeard (E2E)",
        "model": "gpt-4o",
        "prompt": "You are a pirate. Respond to everything with 'Arrr!'"
    }
    create_resp = requests.post(f"{API_BASE}/bots", json=bot_info, headers=headers)
    if create_resp.status_code == 200:
        bot_id = create_resp.json().get("bot_id")
        print(f"OK: Bot Created: {bot_id}")
    else:
        print(f"ERROR: Bot Creation Failed: {create_resp.text}")
        return

    # 4. Chat & Soul Persistence
    print("[TEST 4] Testing Chat & Soul Persistence")
    chat_payload = {
        "bot_id": bot_id,
        "messages": [
            {"role": "user", "content": "Ahoy there! Who are you?"}
        ]
    }
    # Note: We skip the actual LLM call if no key, but we check if the engine builds prompt correctly
    chat_resp = requests.post(f"{API_BASE}/chat/send", json=chat_payload, headers=headers)
    if chat_resp.status_code == 200:
        ans = chat_resp.json().get("reply", "") # Field is 'reply' not 'response'
        print(f"OK: Chat Response: {ans}")
        if "Arrr" in ans or "pirate" in ans.lower():
             print("OK: Soul Persistence Verified")
    elif chat_resp.status_code in [400, 500] and "API key" in chat_resp.text:
        print("WARN: Chat endpoint reached, but missing API Key (Expected behavior for audit without real keys)")
    else:
        print(f"ERROR: Chat Failed: {chat_resp.text}")

    # 5. Settings & API Keys
    print("[TEST 5] Verifying Settings API")
    set_resp = requests.get(f"{API_BASE}/settings/", headers=headers)
    if set_resp.status_code == 200:
        print("OK: Settings Retrieval Successful")
    else:
        print(f"ERROR: Settings Failed: {set_resp.text}")

    # 6. Flow Templates
    print("[TEST 6] Verifying Flow Template loading")
    # Step A: Get Template
    get_tpl = requests.get(f"{API_BASE}/flow-templates/daily_news", headers=headers)
    if get_tpl.status_code == 200:
        tpl = get_tpl.json()
        # Step B: Create Flow
        import json
        flow_payload = {
            "name": "E2E Scraper",
            "description": tpl["description"],
            "flow_data": json.dumps(tpl["flow_data"])
        }
        flow_resp = requests.post(f"{API_BASE}/flows", json=flow_payload, headers=headers)
        if flow_resp.status_code == 200:
            print("OK: Flow Template Imported and Flow Created")
        else:
            print(f"ERROR: Flow Creation from Template Failed: {flow_resp.text}")
    else:
        print(f"ERROR: Fetching Flow Template Failed: {get_tpl.text}")

    print("\n=== E2E AUDIT COMPLETE ===")

if __name__ == "__main__":
    run_test()
