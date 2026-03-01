import os
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

VECTOR_DIR = Path("data/vector_cache")
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

class VectorCache:
    """
    Caches document embeddings locally to accelerate RAG searches.
    """
    
    def __init__(self):
        self.index_file = VECTOR_DIR / "vector_index.json"
        self._load_index()

    def _load_index(self):
        if self.index_file.exists():
            try:
                with open(self.index_file, "r") as f:
                    self.index = json.load(f)
            except:
                self.index = {}
        else:
            self.index = {}

    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Retrieves a cached vector for a given text chunk."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return self.index.get(text_hash)

    def cache_embedding(self, text: str, vector: List[float]):
        """Stores a vector in the local cache."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        self.index[text_hash] = vector
        
        with open(self.index_file, "w") as f:
            json.dump(self.index, f)

    def clear_cache(self):
        self.index = {}
        if self.index_file.exists():
            os.remove(self.index_file)

# Singleton
vector_cache = VectorCache()
