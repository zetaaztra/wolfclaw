import time
import importlib
import sys
import os

modules = [
    "api.routes.auth", "api.routes.bots", "api.routes.settings", "api.routes.remote",
    "api.routes.chat", "api.routes.channels", "api.routes.account", "api.routes.tools",
    "api.routes.templates", "api.routes.favorites", "api.routes.documents",
    "api.routes.history", "api.routes.knowledge", "api.routes.analytics",
    "api.routes.scheduler", "api.routes.reports", "api.routes.flows",
    "api.routes.integrations", "api.routes.macros", "api.routes.marketplace",
    "api.routes.flow_templates"
]

# Ensure we can import from the root
sys.path.append(os.getcwd())

print("Testing imports...")
for mod in modules:
    start = time.time()
    try:
        importlib.import_module(mod)
        end = time.time()
        print(f"SUCCESS: {mod} loaded in {end - start:.4f}s")
    except Exception as e:
        end = time.time()
        print(f"FAILED: {mod} failed after {end - start:.4f}s: {e}")

print("\nImport diagnostic complete.")
