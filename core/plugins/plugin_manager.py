import os
import sys
import importlib.util
import logging
from pathlib import Path

# Set up local plugins directory
PLUGINS_DIR = Path.home() / "wolfclaw_plugins"
PLUGINS_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)

class PluginManager:
    def __init__(self):
        self.plugins = {}
        self.load_all_plugins()

    def load_all_plugins(self):
        self.plugins = {}
        if not PLUGINS_DIR.exists():
            return

        for filename in os.listdir(PLUGINS_DIR):
            if filename.endswith(".py"):
                plugin_name = filename[:-3]
                filepath = PLUGINS_DIR / filename
                self._load_plugin(plugin_name, filepath)

    def _load_plugin(self, name, filepath):
        try:
            spec = importlib.util.spec_from_file_location(name, filepath)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)

            # Check for required exports
            schemas = getattr(module, "PLUGIN_TOOL_SCHEMAS", [])
            execute_fn = getattr(module, "execute_plugin_tool", None)

            if schemas and execute_fn:
                self.plugins[name] = {
                    "module": module,
                    "schemas": schemas,
                    "execute": execute_fn
                }
                logger.info(f"Loaded plugin: {name} ({len(schemas)} tools)")
            else:
                logger.warning(f"Plugin {name} missing PLUGIN_TOOL_SCHEMAS or execute_plugin_tool.")

        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")

        return schemas

    def execute_tool(self, tool_name, kwargs):
        """Dispatches execution to the appropriate plugin if found."""
        for p in self.plugins.values():
            for schema in p["schemas"]:
                if schema["type"] == "function" and schema["function"]["name"] == tool_name:
                    try:
                        return p["execute"](tool_name, kwargs)
                    except Exception as e:
                        return f"Plugin tool error: {str(e)}"
    def get_all_tool_schemas(self):
        """Returns all tool schemas across all loaded plugins."""
        schemas = []
        for p in self.plugins.values():
            schemas.extend(p["schemas"])
        return schemas

    def install_plugin(self, name: str, code: str):
        filepath = PLUGINS_DIR / f"{name}.py"
        with open(filepath, "w") as f:
            f.write(code)
        self.load_all_plugins()
        return True

    def uninstall_plugin(self, name: str):
        filepath = PLUGINS_DIR / f"{name}.py"
        if filepath.exists():
            os.remove(filepath)
            self.load_all_plugins()
            return True
        return False

class RegistryClient:
    """Fetches plugins from a remote registry (e.g. GitHub)."""
    def __init__(self, registry_url="https://raw.githubusercontent.com/wolfclaw/registry/main/registry.json"):
        self.registry_url = registry_url

    def fetch_registry(self):
        import requests
        try:
            # Attempt to fetch remote registry (will fail if URL doesn't exist yet)
            res = requests.get(self.registry_url, timeout=3)
            if res.status_code == 200:
                return res.json().get("plugins", [])
        except Exception as e:
            logger.warning(f"Failed to fetch remote registry, using fallback: {e}")
            
        # Fallback to local MOCK_STORE in marketplace route
        from api.routes.marketplace import MOCK_STORE
        return [{"id": p["id"], "name": p["name"], "description": p["description"], "author": p["author"], "downloads": p["downloads"], "code": p["code"]} for p in MOCK_STORE]

plugin_manager = PluginManager()
registry_client = RegistryClient()
