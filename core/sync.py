import os
import shutil
import logging
from pathlib import Path
from .tunnels import tunnel
from .bot_manager import read_workspace_file, write_workspace_file

logger = logging.getLogger(__name__)

class MemorySync:
    """
    Handles synchronization of MEMORY.md across the sovereign fleet.
    """
    
    def __init__(self):
        self.sync_dir = Path("data/sync_cache")
        self.sync_dir.mkdir(parents=True, exist_ok=True)

    def push_memory(self, bot_id: str):
        """Pushes local memory to the fleet relay via the tunnel."""
        if not tunnel.is_connected:
            logger.warning("Memory sync skipped: Tunnel not connected.")
            return
            
        memory_content = read_workspace_file(bot_id, "MEMORY.md")
        if not memory_content:
            return
            
        packet = {
            "type": "memory_sync_push",
            "bot_id": bot_id,
            "content": memory_content,
            "timestamp": os.path.getmtime(self._get_local_path(bot_id)) if self._get_local_path(bot_id).exists() else 0
        }
        
        # Simulated send via tunnel
        logger.info(f"Pushed memory for bot {bot_id} to fleet.")

    def pull_memory(self, bot_id: str):
        """Pulls latest memory from the fleet relay."""
        if not tunnel.is_connected:
            return
            
        # Simulated pull
        # In practice, this would compare timestamps and keep the latest
        logger.info(f"Pulled latest memory for bot {bot_id} from fleet.")

    def _get_local_path(self, bot_id: str) -> Path:
        # Assuming typical workspace structure
        return Path(f"workspaces/default/bots/{bot_id}/MEMORY.md")

# Singleton
memory_sync = MemorySync()
