from fastapi import APIRouter, HTTPException
import os
from pathlib import Path
from core.plugins.plugin_manager import PLUGINS_DIR, plugin_manager

router = APIRouter()

MOCK_STORE = [
    {
        "id": "salesforce_connector",
        "name": "Salesforce Query",
        "description": "Custom query runner for Salesforce CRM.",
        "author": "Community",
        "downloads": 1240,
        "code": """
PLUGIN_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "salesforce_query",
            "description": "Run a SOQL query against Salesforce.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The SOQL query string"}
                },
                "required": ["query"]
            }
        }
    }
]

def execute_plugin_tool(name, kwargs):
    if name == "salesforce_query":
        return f"Mock Salesforce Result for query: {kwargs.get('query')}"
    return None
"""
    },
    {
        "id": "math_calculator",
        "name": "Advanced Calculator",
        "description": "Perform complex mathematical operations.",
        "author": "Wolfclaw Team",
        "downloads": 5400,
        "code": """
import math

PLUGIN_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_math",
            "description": "Evaluate a mathematical expression. ONLY math functions allowd (e.g. math.sin(x), math.sqrt(y)).",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression string"}
                },
                "required": ["expression"]
            }
        }
    }
]

def execute_plugin_tool(name, kwargs):
    if name == "calculate_math":
        try:
            allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
            result = eval(kwargs.get("expression", ""), {"__builtins__": {}}, allowed_names)
            return str(result)
        except Exception as e:
            return f"Math parsing error: {str(e)}"
    return None
"""
    }
]

@router.get("/plugins")
async def list_store_plugins():
    return {"plugins": [
        {"id": p["id"], "name": p["name"], "description": p["description"], "author": p["author"], "downloads": p["downloads"]}
        for p in MOCK_STORE
    ]}

@router.get("/installed")
async def list_installed_plugins():
    installed = []
    if PLUGINS_DIR.exists():
        for filename in os.listdir(PLUGINS_DIR):
            if filename.endswith(".py"):
                installed.append(filename[:-3])
    return {"installed": installed}

@router.post("/install/{plugin_id}")
async def install_plugin(plugin_id: str):
    plugin = next((p for p in MOCK_STORE if p["id"] == plugin_id), None)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found in store.")
        
    filepath = PLUGINS_DIR / f"{plugin_id}.py"
    try:
        with open(filepath, "w") as f:
            f.write(plugin["code"])
            
        # Hot-reload plugins
        plugin_manager.load_all_plugins()
        return {"status": "success", "message": f"{plugin['name']} installed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/uninstall/{plugin_id}")
async def uninstall_plugin(plugin_id: str):
    filepath = PLUGINS_DIR / f"{plugin_id}.py"
    if filepath.exists():
        try:
            os.remove(filepath)
            plugin_manager.load_all_plugins()
            return {"status": "success", "message": f"{plugin_id} uninstalled."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=404, detail="Plugin not installed.")
