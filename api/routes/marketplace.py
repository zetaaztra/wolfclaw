from fastapi import APIRouter, HTTPException, Query
import os
from pathlib import Path
from core.plugins.plugin_manager import PLUGINS_DIR, plugin_manager
from data.plugin_catalog import PLUGIN_CATALOG

router = APIRouter()

# The full catalog (90 plugins across 11 personas)
MOCK_STORE = PLUGIN_CATALOG

@router.get("/plugins")
async def list_store_plugins(
    tier: int = Query(None, description="Filter by tier (0-10)"),
    persona: str = Query(None, description="Filter by persona"),
    search: str = Query(None, description="Search by name or description")
):
    plugins = MOCK_STORE
    if tier is not None:
        plugins = [p for p in plugins if p.get("tier") == tier]
    if persona:
        plugins = [p for p in plugins if persona.lower() in p.get("persona", "").lower()]
    if search:
        q = search.lower()
        plugins = [p for p in plugins if q in p["name"].lower() or q in p["description"].lower()]
    return {"plugins": [
        {"id": p["id"], "name": p["name"], "description": p["description"],
         "author": p.get("author", "Community"), "downloads": p.get("downloads", 0),
         "tier": p.get("tier", 0), "persona": p.get("persona", "")}
        for p in plugins
    ], "total": len(plugins)}

@router.get("/tiers")
async def list_tiers():
    """Return available tiers and plugin counts."""
    tiers = {}
    for p in MOCK_STORE:
        t = p.get("tier", 0)
        persona = p.get("persona", "Unknown")
        if t not in tiers:
            tiers[t] = {"tier": t, "persona": persona, "count": 0}
        tiers[t]["count"] += 1
    return {"tiers": list(tiers.values())}

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

