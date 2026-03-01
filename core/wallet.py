import os
import json
import threading
from datetime import datetime, date
from pathlib import Path

WALLET_DIR = Path("data/wallet")
WALLET_DIR.mkdir(parents=True, exist_ok=True)

_wallet_lock = threading.Lock()

def _get_wallet_file(bot_id: str) -> Path:
    return WALLET_DIR / f"{bot_id}_wallet.json"

def get_budget_status(bot_id: str):
    """Returns the current budget configuration and today's spend."""
    wallet_file = _get_wallet_file(bot_id)
    if not wallet_file.exists():
        return {"daily_budget": 5.0, "today_spend": 0.0, "is_active": True, "total_spend": 0.0}
        
    try:
        with open(wallet_file, "r") as f:
            data = json.load(f)
            
        today = date.today().isoformat()
        if data.get("last_reset") != today:
            data["today_spend"] = 0.0
            data["last_reset"] = today
            with open(wallet_file, "w") as f:
                json.dump(data, f)
                
        return data
    except:
        return {"daily_budget": 5.0, "today_spend": 0.0, "is_active": True, "total_spend": 0.0}

def set_daily_budget(bot_id: str, amount: float):
    """Sets the daily budget for a bot."""
    with _wallet_lock:
        data = get_budget_status(bot_id)
        data["daily_budget"] = amount
        
        with open(_get_wallet_file(bot_id), "w") as f:
            json.dump(data, f)

def log_spend(bot_id: str, amount: float):
    """Records an expenditure."""
    with _wallet_lock:
        data = get_budget_status(bot_id)
        data["today_spend"] += amount
        data["total_spend"] = data.get("total_spend", 0.0) + amount
        
        with open(_get_wallet_file(bot_id), "w") as f:
            json.dump(data, f)

def check_budget(bot_id: str) -> bool:
    """Returns True if the bot has remaining budget for today."""
    status = get_budget_status(bot_id)
    if status["today_spend"] >= status["daily_budget"]:
        return False
    return True

def get_wallet_summary(bot_id: str):
    """Returns a view-friendly summary of the bot's wallet."""
    data = get_budget_status(bot_id)
    remaining = max(0, data["daily_budget"] - data["today_spend"])
    return {
        "daily_budget": data["daily_budget"],
        "today_spend": round(data["today_spend"], 4),
        "remaining": round(remaining, 4),
        "percent_used": (data["today_spend"] / data["daily_budget"] * 100) if data["daily_budget"] > 0 else 0
    }
