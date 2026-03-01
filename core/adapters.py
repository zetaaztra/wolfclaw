import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ADAPTERS_DIR = Path("core/adapters_data")
ADAPTERS_DIR.mkdir(parents=True, exist_ok=True)

# Default built-in adapters (simulated data)
DEFAULT_ADAPTERS = {
    "chrome": {
        "elements": {
            "address_bar": {"selector": "url_bar", "type": "input"},
            "new_tab": {"selector": "new_tab_button", "type": "button"}
        }
    },
    "excel": {
        "elements": {
            "file_menu": {"selector": "file_tab", "type": "menu"},
            "save": {"selector": "save_icon", "type": "button"}
        }
    }
}

class AppAdapterManager:
    """
    Manages pre-defined UI maps for common applications.
    """
    
    def __init__(self):
        self.adapters = DEFAULT_ADAPTERS

    def get_adapter(self, app_name: str) -> Optional[Dict]:
        """Retrieves the element map for a specific application."""
        return self.adapters.get(app_name.lower())

    def register_adapter(self, app_name: str, element_map: Dict):
        """Allows adding new application maps at runtime."""
        self.adapters[app_name.lower()] = element_map
        logger.info(f"Registered universal adapter for {app_name}")

    def list_available_apps(self) -> List[str]:
        return list(self.adapters.keys())

# Singleton
adapter_manager = AppAdapterManager()
