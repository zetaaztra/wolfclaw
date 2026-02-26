import os
import sys
import multiprocessing
import threading
import time
import webbrowser
import uvicorn
import urllib.request
import logging

def get_base_dir():
    """Get the base directory for the application."""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), '_internal', 'wolfclaw_app')
    else:
        return os.path.dirname(os.path.abspath(__file__))

def setup_logging():
    """Redirect logs to a file in the user's home directory."""
    log_dir = os.path.join(os.path.expanduser("~"), ".wolfclaw")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "wolfclaw.log")
    
    # Simple redirection for packaged exe
    if getattr(sys, 'frozen', False):
        f = open(log_file, 'a', encoding='utf-8')
        sys.stdout = f
        sys.stderr = f
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("WolfclawLauncher")

def find_available_port(start_port=8501, max_attempts=20):
    """Find an available port starting from start_port."""
    import socket
    port = start_port
    while port < start_port + max_attempts:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
        port += 1
    return start_port

def start_backend(port, base_dir, logger):
    """Function to run Uvicorn using Server/Config for better thread control."""
    try:
        sys.path.insert(0, base_dir)
        # Import inside the thread to avoid issues with some libraries
        from api.main import app
        
        logger.info(f"Uvicorn: Starting server on 127.0.0.1:{port}")
        config = uvicorn.Config(app, host="127.0.0.1", port=int(port), log_level="info")
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.error(f"BACKEND CRITICAL FAILURE: {e}")
        import traceback
        logger.error(traceback.format_exc())

def wait_for_backend(url, logger, timeout=60):
    """Poll the health check endpoint until it responds or times out."""
    start_time = time.time()
    health_url = f"{url}/api/health"
    logger.info(f"Polling {health_url}...")
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(health_url) as response:
                if response.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    multiprocessing.freeze_support()
    logger = setup_logging()
    
    base_dir = get_base_dir()
    os.environ["WOLFCLAW_ENVIRONMENT"] = "desktop"
    
    sys.path.insert(0, base_dir)
    if "PYTHONPATH" in os.environ:
        os.environ["PYTHONPATH"] = f"{base_dir}{os.pathsep}{os.environ['PYTHONPATH']}"
    else:
        os.environ["PYTHONPATH"] = base_dir

    logger.info("==================================================")
    logger.info(" Wolfclaw AI Desktop Engine (Native Web App)")
    logger.info("==================================================")
    logger.info(f"Base directory: {base_dir}")
    
    # 1. Automatic Port Discovery
    port = find_available_port(8501)
    url = f"http://127.0.0.1:{port}"

    logger.info(f"Starting Native Backend on {url}...")
    daemon = threading.Thread(target=start_backend, args=(port, base_dir, logger), daemon=True)
    daemon.start()

    logger.info("Waiting for server to boot (Health Check)...")
    if wait_for_backend(url, logger):
        logger.info(f"Server ready! Opening Native Window at {url}")
    else:
        logger.error("Backend health check timed out. The server might have failed to start or is blocked by a firewall.")
        # We still try to open webview to show the error page which helps debugging
    
    try:
        import webview
        logger.info("Initializing PyWebView window...")
        # Note: private_mode=False is important for local storage persistence
        webview.create_window('Wolfclaw AI Command Center', url, width=1280, height=800)
        webview.start(private_mode=False, debug=getattr(sys, 'frozen', False)) 
    except Exception as e:
        logger.error(f"Native window failed, falling back to browser: {e}")
        webbrowser.open(url)
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            pass

    logger.info("Shutting down Wolfclaw...")

if __name__ == '__main__':
    main()
