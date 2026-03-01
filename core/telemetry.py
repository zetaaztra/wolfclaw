import os
import json
import logging
import requests
from pathlib import Path
from .config import get_setting # Hypothetical setting getter

logger = logging.getLogger(__name__)

TELEMETRY_ENDPOINT = "https://telemetry.wolfclaw.ai/v1/collect"

def log_telemetry(event_type: str, data: dict):
    """
    Logs an anonymized telemetry event if the user has opted in.
    """
    # Check opt-in status (Default is False for 'Sovereign' privacy)
    try:
        from core.local_db import get_setting
        opt_in = get_setting("telemetry_opt_in") == "true"
    except:
        opt_in = False
        
    if not opt_in:
        return
        
    packet = {
        "event": event_type,
        "payload": data,
        "os": os.name,
        "wolfclaw_version": "3.1.0-Sovereign"
    }
    
    # Send asynchronously (simulated)
    try:
        # requests.post(TELEMETRY_ENDPOINT, json=packet, timeout=2)
        logger.info(f"Telemetry logged: {event_type}")
    except Exception as e:
        logger.debug(f"Telemetry delivery failed: {e}")

def get_telemetry_report():
    """Aggregates local usage for the dashboard before anonymization."""
    from core.metrics import get_metrics_summary
    return get_metrics_summary("all")
