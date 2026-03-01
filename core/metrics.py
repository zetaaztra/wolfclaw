import os
import json
import time
from datetime import datetime
from pathlib import Path

# Base directory for metrics data
METRICS_DIR = Path("data/metrics")
METRICS_DIR.mkdir(parents=True, exist_ok=True)

def _get_metric_file(bot_id: str) -> Path:
    return METRICS_DIR / f"{bot_id}_events.json"

def log_event(bot_id: str, event_type: str, status: str = "success", details: dict = None):
    """
    Logs an event for a specific bot.
    event_type: 'tool_call', 'flow_start', 'flow_complete', 'chat_message', 'error'
    """
    if not bot_id:
        return
        
    metric_file = _get_metric_file(bot_id)
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "status": status,
        "details": details or {}
    }
    
    events = []
    if metric_file.exists():
        try:
            with open(metric_file, "r") as f:
                events = json.load(f)
        except:
            events = []
            
    events.append(event)
    
    # Keep only the last 1000 events to prevent file bloat
    if len(events) > 1000:
        events = events[-1000:]
        
    with open(metric_file, "w") as f:
        json.dump(events, f, indent=2)

def get_metrics_summary(bot_id: str):
    """
    Returns aggregated metrics for a bot to be used in UI graphs.
    """
    metric_file = _get_metric_file(bot_id)
    if not metric_file.exists():
        return {
            "total_calls": 0,
            "success_rate": 0,
            "tool_usage": {},
            "activity_over_time": []
        }
        
    try:
        with open(metric_file, "r") as f:
            events = json.load(f)
    except:
        return {}

    summary = {
        "total_calls": 0,
        "success_rate": 0,
        "tool_usage": {},
        "activity_over_time": [] # List of (timestamp, count)
    }
    
    successes = 0
    tool_counts = {}
    time_series = {} # bucket by hour or day
    
    for event in events:
        summary["total_calls"] += 1
        if event["status"] == "success":
            successes += 1
            
        # Count tool usage
        if event["type"] == "tool_call":
            tool_name = event["details"].get("tool_name", "unknown")
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
            
        # Time series (bucketed by hour for the graph)
        ts = datetime.fromisoformat(event["timestamp"]).strftime("%Y-%m-%d %H:00")
        time_series[ts] = time_series.get(ts, 0) + 1
        
    summary["success_rate"] = (successes / summary["total_calls"]) * 100 if summary["total_calls"] > 0 else 0
    summary["tool_usage"] = tool_counts
    
    # Convert time_series dict to sorted list of objects for Streamlit/Chart
    sorted_ts = sorted(time_series.items())
    summary["activity_over_time"] = [{"time": t, "count": c} for t, c in sorted_ts]
    
    return summary
