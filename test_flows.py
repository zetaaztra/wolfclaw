import sys
import json
import logging
import os
import asyncio

# Setup path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.local_db import save_flow, get_flows_for_workspace
from core.bot_manager import _get_active_workspace_id
from core.flow_engine import run_flow

logging.basicConfig(level=logging.INFO)

def test_flow():
    ws_id = _get_active_workspace_id()
    if not ws_id:
        print("No active workspace found.")
        return

    print(f"Active WS: {ws_id}")

    # Build a simple mock flow
    # 1. Manual Trigger -> 2. Web Search ("weather in Tokyo") -> 3. Output
    flow_data = {
        "nodes": {
            "node_1": {
                "type": "manual_trigger",
                "config": {},
                "position": {"x": 100, "y": 100}
            },
            "node_2": {
                "type": "web_search",
                "config": {"query": "current weather in Tokyo 2026"},
                "position": {"x": 300, "y": 100}
            },
            "node_3": {
                "type": "output",
                "config": {"message": "Search returned: {{node_2.results}}"},
                "position": {"x": 500, "y": 100}
            }
        },
        "edges": [
            {"from": "node_1", "to": "node_2"},
            {"from": "node_2", "to": "node_3"}
        ]
    }

    # Save to local DB
    flow_id = save_flow(ws_id, "Test Weather Flow", "A test flow created by code", json.dumps(flow_data))
    print(f"Saved flow with ID: {flow_id}")

    # Execute it directly
    print("Executing flow...")
    result = run_flow(flow_data)
    
    print("\n--- Flow Execution Result ---")
    print(f"Status: {result.get('status')}")
    print(f"Elapsed: {result.get('elapsed_seconds')}s")
    
    print("\n--- Execution Log ---")
    for log in result.get("log", []):
        print(f"[{log['node_id']}] {log['type']}: {log['status']}")
        if log['status'] == 'error':
            print(f"Error: {log['error']}")
    
    print("\n--- Final Context Output ---")
    print(result.get("final_context", {}).get("node_3.message", "No output message"))

if __name__ == "__main__":
    test_flow()
