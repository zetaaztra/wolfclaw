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

    def get_all_tool_schemas(self):
        schemas = []
        for p in self.plugins.values():
            schemas.extend(p["schemas"])
        return schemas

    def execute_tool(self, tool_name, kwargs):
        """Dispatches execution to the appropriate plugin if found."""
        for p in self.plugins.values():
            # Check if this plugin owns the tool
            for schema in p["schemas"]:
                if schema["type"] == "function" and schema["function"]["name"] == tool_name:
                    try:
                        return p["execute"](tool_name, kwargs)
                    except Exception as e:
                        return f"Plugin tool error: {str(e)}"
        
        return None # Not a plugin tool

plugin_manager = PluginManager()
