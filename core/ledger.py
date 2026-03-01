import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

LEDGER_DIR = Path("data/ledger")
LEDGER_DIR.mkdir(parents=True, exist_ok=True)

def _get_ledger_file(bot_id: str) -> Path:
    return LEDGER_DIR / f"{bot_id}.ledger"

def _compute_hash(entry: dict, previous_hash: str) -> str:
    """Computes a SHA-256 hash of the entry content + previous hash."""
    entry_string = json.dumps(entry, sort_keys=True)
    return hashlib.sha256(f"{entry_string}{previous_hash}".encode()).hexdigest()

def log_mutation(bot_id: str, action: str, details: dict):
    """
    Logs a system mutation (tool call, file change, etc.) to the proof ledger.
    Uses hash chaining to detect tampering.
    """
    if not bot_id:
        return
        
    ledger_file = _get_ledger_file(bot_id)
    
    # Load last entry to get its hash
    previous_hash = "GENESIS"
    if ledger_file.exists():
        try:
            with open(ledger_file, "r") as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    previous_hash = last_entry.get("hash", "GENESIS")
        except:
            pass
            
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details,
        "previous_hash": previous_hash
    }
    
    # Compute the hash for this new entry
    entry["hash"] = _compute_hash(entry, previous_hash)
    
    # Append to ledger (one JSON object per line)
    with open(ledger_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

def verify_ledger(bot_id: str) -> bool:
    """
    Verifies the integrity of the ledger for a specific bot.
    Returns True if valid, False if tampering is detected.
    """
    ledger_file = _get_ledger_file(bot_id)
    if not ledger_file.exists():
        return True
        
    try:
        with open(ledger_file, "r") as f:
            lines = f.readlines()
            
        current_previous_hash = "GENESIS"
        for i, line in enumerate(lines):
            entry = json.loads(line)
            
            # 1. Verify links
            if entry.get("previous_hash") != current_previous_hash:
                print(f"FAILED: Hash link broken at entry {i}")
                return False
                
            # 2. Recompute current hash
            recomputed = _compute_hash(
                {k: v for k, v in entry.items() if k != "hash"}, 
                current_previous_hash
            )
            
            if entry.get("hash") != recomputed:
                print(f"FAILED: Hash mismatch at entry {i}")
                return False
                
            current_previous_hash = entry.get("hash")
            
        return True
    except Exception as e:
        print(f"ERROR: Ledger verification failed: {e}")
        return False

def get_ledger_entries(bot_id: str, limit: int = 50):
    """Retrieves the most recent entries from the ledger."""
    ledger_file = _get_ledger_file(bot_id)
    if not ledger_file.exists():
        return []
        
    try:
        with open(ledger_file, "r") as f:
            lines = f.readlines()
            return [json.loads(line) for line in lines[-limit:]]
    except:
        return []
