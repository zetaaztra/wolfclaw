import subprocess
import time
import os
import requests
import sys

def wait_for_server(url, timeout=60):
    start = time.time()
    print(f"[AUDIT] Waiting up to {timeout}s for {url}...")
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                print(f"[AUDIT] Server responded in {int(time.time() - start)}s.")
                return True
        except:
            pass
        time.sleep(1)
    return False

def main():
    print("--- Wolfclaw Audit Runner ---")
    
    # Set environment
    os.environ["WOLFCLAW_ENVIRONMENT"] = "desktop"
    
    # Clear local DB for clean audit
    db_path = os.path.join(os.path.expanduser("~"), ".wolfclaw", "wolfclaw_local.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"[AUDIT] Cleared existing database at {db_path}")
        except Exception as e:
            print(f"[AUDIT] Warning: Could not clear database: {e}")
    
    # Start server
    audit_log_path = "server_audit.log"
    print(f"[AUDIT] Starting FastAPI server (Logs: {audit_log_path})...")
    
    # Ensure unbuffered output so we see logs immediately
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    with open(audit_log_path, "w") as log_file:
        log_file.write(f"--- Audit Session Started at {time.ctime()} ---\n")
        log_file.flush()
        
    log_file = open(audit_log_path, "a", buffering=1) # Line buffered
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8501", "--log-level", "debug"],
        cwd=os.path.join(os.getcwd(), "wolfclaw"),
        env=env,
        stdout=log_file,
        stderr=log_file
    )
    
    try:
        print("[AUDIT] Waiting for server to boot...")
        if wait_for_server("http://localhost:8501/api/health"):
            print("[AUDIT] Server is UP. Initiating E2E Tests.")
            
            # Run test script
            test_script = os.path.join(os.getcwd(), "wolfclaw", "e2e_integration_test.py")
            print(f"[AUDIT] Executing: {test_script}")
            subprocess.run([sys.executable, test_script], env=os.environ.copy())
            print("[AUDIT] E2E Selection Finished.")
        else:
            print("[AUDIT] ERROR: Server failed to start in time.")
            
    finally:
        print("[AUDIT] Shutting down server...")
        server_proc.terminate()
        server_proc.wait()

if __name__ == "__main__":
    main()
