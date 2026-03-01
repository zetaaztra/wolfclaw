import requests
import json

API_BASE = "http://localhost:8501/api"

def test_command_injection():
    print("Testing Command Injection in run_terminal_command...")
    # This test assumes we can call the tool via a bot
    # For direct testing, we check if the _is_command_safe filter works
    payload = "ls ; rm -rf /"
    # We would check the backend logic directly or via mocked chat
    print(f"Payload: {payload}")
    print("Result: Should be blocked by SECURITY ABORT.")

def test_auth_bypass():
    print("Testing Auth Bypass...")
    resp = requests.get(f"{API_BASE}/bots")
    if resp.status_code == 403 or resp.status_code == 401:
        print("Success: Access restricted.")
    else:
        print(f"Warning: Unexpected status {resp.status_code}")

def test_ssrf():
    print("Testing SSRF in Flow Engine...")
    # Attempt to hit local metadata or generic local service
    local_url = "http://192.168.1.1" # Hypothetical router
    print(f"Payload: {local_url}")
    print("Result: Should be blocked by Security Block.")

if __name__ == "__main__":
    print("=== Wolfclaw Security Audit ===")
    test_auth_bypass()
    test_command_injection()
    test_ssrf()
