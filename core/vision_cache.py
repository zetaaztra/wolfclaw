import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/vision_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class VisionCache:
    """
    Caches UI landmarks to speed up screen-aware tool execution.
    """
    
    def __init__(self):
        self.cache_file = CACHE_DIR / "landmarks.json"
        self._load_cache()

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    self.data = json.load(f)
            except:
                self.data = {}
        else:
            self.data = {}

    def save_landmark(self, app_name: str, element_name: str, coordinates: tuple, signature: str = None):
        """Saves a UI element's location and visual hash."""
        key = f"{app_name}:{element_name}"
        self.data[key] = {
            "x": coordinates[0],
            "y": coordinates[1],
            "signature": signature,
            "last_seen": os.path.getmtime(self.cache_file) if self.cache_file.exists() else 0
        }
        
        with open(self.cache_file, "w") as f:
            json.dump(self.data, f)

    def get_landmark(self, app_name: str, element_name: str) -> Optional[Dict]:
        """Retrieves cached location for a UI element."""
        return self.data.get(f"{app_name}:{element_name}")

    def clear_cache(self):
        self.data = {}
        if self.cache_file.exists():
            os.remove(self.cache_file)

# Singleton
vision_cache = VisionCache()
