"""
Wolfclaw Flows — DAG-based Visual Workflow Engine

Each flow is a JSON graph of blocks (nodes) connected by edges.
The engine resolves execution order via topological sort and passes
data between blocks through a shared context dictionary.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from core.ledger import log_mutation

logger = logging.getLogger(__name__)

# ─────────── BLOCK REGISTRY ───────────
# Maps block type strings to executor functions.
# Each executor receives (config: dict, context: dict, bot_id: str) and returns a result.

def _exec_manual_trigger(config: dict, context: dict, bot_id: str) -> dict:
    """Manual trigger with timezone support."""
    timezone = config.get("timezone", "UTC").upper()
    from datetime import datetime, timezone as dt_tz, timedelta
    tz_offsets = {"UTC": 0, "IST": 5.5, "EST": -5, "PST": -8}
    offset = tz_offsets.get(timezone, 0)
    current_time = datetime.now(dt_tz.utc) + timedelta(hours=offset)
    formatted_time = current_time.strftime("%I:%M %p %Z")
    return {"triggered": True, "timestamp": formatted_time, "timezone": timezone}


def _exec_schedule_trigger(config: dict, context: dict, bot_id: str) -> dict:
    """Schedule trigger — stores cron expression. Actual scheduling is handled by the scheduler."""
    return {"cron": config.get("cron", ""), "scheduled": True}


def _exec_ai_prompt(config: dict, context: dict, bot_id: str) -> dict:
    """Send a prompt to the LLM engine and return the response."""
    from core.llm_engine import WolfEngine

    model = config.get("model", "gpt-4o")
    prompt_template = config.get("prompt", "")
    system = config.get("system_prompt", "You are a helpful assistant.")

    # Resolve template variables from context
    prompt = prompt_template
    for key, value in context.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

    engine = WolfEngine(model)
    messages = [{"role": "user", "content": prompt}]
    
    # Log to ledger
    if bot_id:
        log_mutation(bot_id, "flow_ai_call", {"model": model, "prompt": prompt[:100]})

    try:
        response = engine.chat(messages, system_prompt=system, stream=False, bot_id=bot_id)
        reply = response.choices[0].message.content
        return {"response": reply}
    except Exception as e:
        return {"error": str(e)}


def _exec_terminal_command(config: dict, context: dict, bot_id: str) -> dict:
    """Execute a local terminal command."""
    from core.tools import run_terminal_command
    command = config.get("command", "")
    # Resolve template variables
    for key, value in context.items():
        command = command.replace(f"{{{{{key}}}}}", str(value))
    
    # Log to ledger
    if bot_id:
        log_mutation(bot_id, "flow_terminal_exec", {"command": command})

    result = run_terminal_command(command)
    return {"output": result}


def _exec_web_search(config: dict, context: dict, bot_id: str) -> dict:
    """Run a web search query."""
    from core.tools import web_search as web_search_tool
    query = config.get("query", "")
    for key, value in context.items():
        query = query.replace(f"{{{{{key}}}}}", str(value))
    
    # Log to ledger
    if bot_id:
        log_mutation(bot_id, "flow_web_search", {"query": query})

    result = web_search_tool(query)
    return {"results": result}


def _exec_condition(config: dict, context: dict, bot_id: str) -> dict:
    """Evaluate a condition. Returns which branch to follow (true/false)."""
    field = config.get("field", "")
    operator = config.get("operator", "==")
    value = config.get("value", "")
    
    actual = str(context.get(field, ""))
    
    if operator == "==":
        passed = actual == value
    elif operator == "!=":
        passed = actual != value
    elif operator == "contains":
        passed = value in actual
    elif operator == "not_contains":
        passed = value not in actual
    elif operator == ">":
        try: passed = float(actual) > float(value)
        except: passed = False
    elif operator == "<":
        try: passed = float(actual) < float(value)
        except: passed = False
    else:
        passed = False
    
    return {"passed": passed, "branch": "true" if passed else "false"}


def _exec_output(config: dict, context: dict, bot_id: str) -> dict:
    """Output block — formats and returns the final result."""
    template = config.get("message", "Flow completed.")
    for key, value in context.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    
    return {"message": template}


def _exec_screenshot(config: dict, context: dict, bot_id: str) -> dict:
    """Take a screenshot of the current screen."""
    from core.tools import capture_screenshot
    result = capture_screenshot()
    return {"screenshot": result}


def _is_safe_url(url: str) -> bool:
    """SSRF protection: prevent requests to local network/private IPs."""
    from urllib.parse import urlparse
    import socket
    
    try:
        parsed = urlparse(url)
        # Always allow Ollama
        if parsed.netloc == "localhost:11434" or parsed.netloc == "127.0.0.1:11434":
            return True
            
        host = parsed.hostname
        if not host:
            return False
            
        ip = socket.gethostbyname(host)
        
        # Private IP ranges (RFC 1918)
        octets = [int(o) for o in ip.split('.')]
        if octets[0] == 10: return False
        if octets[0] == 172 and (16 <= octets[1] <= 31): return False
        if octets[0] == 192 and octets[1] == 168: return False
        if octets[0] == 127: return False
        
        return True
    except:
        return False

def _exec_http_request(config: dict, context: dict, bot_id: str) -> dict:
    """Make an HTTP request."""
    import requests as req_lib
    
    url = config.get("url", "")
    method = config.get("method", "GET").upper()
    headers = config.get("headers", {})
    body = config.get("body", "")
    
    # Resolve templates
    for key, value in context.items():
        url = url.replace(f"{{{{{key}}}}}", str(value))
        body = body.replace(f"{{{{{key}}}}}", str(value))
    
    if not _is_safe_url(url):
        return {"error": f"Security Block: URL '{url}' is restricted (Local/Private IP)."}

    # Log to ledger
    if bot_id:
        log_mutation(bot_id, "flow_http_request", {"url": url, "method": method})

    try:
        if method == "GET":
            resp = req_lib.get(url, headers=headers, timeout=30)
        elif method == "POST":
            resp = req_lib.post(url, headers=headers, data=body, timeout=30)
        elif method == "PUT":
            resp = req_lib.put(url, headers=headers, data=body, timeout=30)
        elif method == "DELETE":
            resp = resp = req_lib.delete(url, headers=headers, timeout=30)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        return {"status_code": resp.status_code, "body": resp.text[:5000]}
    except Exception as e:
        return {"error": str(e)}


def _exec_delay(config: dict, context: dict, bot_id: str) -> dict:
    """Wait for a specified number of seconds."""
    seconds = config.get("seconds", 1)
    time.sleep(min(seconds, 300))  # Cap at 5 minutes
    return {"waited": seconds}


def _exec_simulate_gui(config: dict, context: dict, bot_id: str) -> dict:
    """Simulate human GUI input with Self-Healing support."""
    from core.tools import simulate_gui
    action = config.get("action", "click")
    keys = config.get("keys", "")
    x = config.get("x", 0)
    y = config.get("y", 0)
    anchor = config.get("anchor_image")
    
    if bot_id:
        from .ledger import log_mutation
        log_mutation(bot_id, "gui_simulation", {"action": action, "target": f"{x},{y}", "anchor": anchor})

    result = simulate_gui(action, keys=keys, x=x, y=y, anchor_image=anchor)
    return {"result": result}

def _exec_send_email(config: dict, context: dict, bot_id: str) -> dict:
    """Simulate sending an email."""
    to_addr = config.get("to", "")
    subject = config.get("subject", "")
    for key, value in context.items():
        to_addr = to_addr.replace(f"{{{{{key}}}}}", str(value))
        subject = subject.replace(f"{{{{{key}}}}}", str(value))
    return {"email_sent_to": to_addr, "subject": subject, "status": "success"}

def _exec_send_telegram(config: dict, context: dict, bot_id: str) -> dict:
    """Send a Telegram message or simulate it."""
    chat_id = config.get("chat_id", "")
    message = config.get("message", "")
    for key, value in context.items():
        chat_id = chat_id.replace(f"{{{{{key}}}}}", str(value))
        message = message.replace(f"{{{{{key}}}}}", str(value))
    return {"telegram_sent_to": chat_id, "message": message, "status": "success"}


# ─────────── BLOCK REGISTRY MAP ───────────

BLOCK_EXECUTORS = {
    "manual_trigger":    _exec_manual_trigger,
    "schedule_trigger":  _exec_schedule_trigger,
    "ai_prompt":         _exec_ai_prompt,
    "terminal_command":  _exec_terminal_command,
    "web_search":        _exec_web_search,
    "condition":         _exec_condition,
    "output":            _exec_output,
    "screenshot":        _exec_screenshot,
    "http_request":      _exec_http_request,
    "delay":             _exec_delay,
    "send_email":        _exec_send_email,
    "send_telegram":     _exec_send_telegram,
    "simulate_gui":      _exec_simulate_gui,
}

# Block metadata for the frontend palette
BLOCK_CATALOG = [
    {"type": "manual_trigger",   "label": "Manual Trigger",   "category": "Triggers",  "color": "#3b82f6", "icon": "fa-play",          "inputs": 0, "outputs": 1},
    {"type": "schedule_trigger", "label": "Schedule Trigger",  "category": "Triggers",  "color": "#3b82f6", "icon": "fa-clock",         "inputs": 0, "outputs": 1},
    {"type": "ai_prompt",        "label": "AI Prompt",         "category": "AI",        "color": "#8b5cf6", "icon": "fa-brain",         "inputs": 1, "outputs": 1},
    {"type": "terminal_command", "label": "Run Command",       "category": "Tools",     "color": "#10b981", "icon": "fa-terminal",      "inputs": 1, "outputs": 1},
    {"type": "web_search",       "label": "Web Search",        "category": "Tools",     "color": "#10b981", "icon": "fa-search",        "inputs": 1, "outputs": 1},
    {"type": "http_request",     "label": "HTTP Request",      "category": "Tools",     "color": "#10b981", "icon": "fa-globe",         "inputs": 1, "outputs": 1},
    {"type": "screenshot",       "label": "Screenshot",        "category": "Tools",     "color": "#10b981", "icon": "fa-camera",        "inputs": 1, "outputs": 1},
    {"type": "condition",        "label": "IF Condition",       "category": "Logic",     "color": "#f59e0b", "icon": "fa-code-branch",   "inputs": 1, "outputs": 2},
    {"type": "delay",            "label": "Wait / Delay",      "category": "Logic",     "color": "#f59e0b", "icon": "fa-hourglass-half","inputs": 1, "outputs": 1},
    {"type": "output",           "label": "Output",            "category": "Outputs",   "color": "#ef4444", "icon": "fa-flag-checkered","inputs": 1, "outputs": 0},
    {"type": "send_email",       "label": "Send Email",        "category": "Outputs",   "color": "#ef4444", "icon": "fa-envelope",      "inputs": 1, "outputs": 0},
    {"type": "send_telegram",    "label": "Send Telegram",     "category": "Outputs",   "color": "#3b82f6", "icon": "fa-paper-plane",   "inputs": 1, "outputs": 0},
    {"type": "simulate_gui",     "label": "GUI Macro Step",    "category": "Tools",     "color": "#10b981", "icon": "fa-mouse-pointer", "inputs": 1, "outputs": 1},
]

# ─────────── FLOW ENGINE ───────────

class FlowEngine:
    def __init__(self, flow_data: dict, bot_id: str = None, max_steps: int = 50):
        self.nodes = flow_data.get("nodes", {})
        self.edges = flow_data.get("edges", [])
        self.bot_id = bot_id
        self.context: Dict[str, Any] = {}
        self.execution_log: List[dict] = []
        self.max_steps = max_steps
        self.step_count = 0
    
    def _topological_sort(self) -> List[str]:
        in_degree = {nid: 0 for nid in self.nodes}
        adjacency = {nid: [] for nid in self.nodes}
        for edge in self.edges:
            src, dst = edge["from"], edge["to"]
            if src in adjacency and dst in in_degree:
                adjacency[src].append(dst)
                in_degree[dst] += 1
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return order
    
    def execute(self) -> dict:
        start_time = time.time()
        order = self._topological_sort()
        results = {}
        for node_id in order:
            if self.step_count >= self.max_steps: break
            self.step_count += 1
            node = self.nodes.get(node_id, {})
            block_type = node.get("type", "")
            config = node.get("config", {})
            executor = BLOCK_EXECUTORS.get(block_type)
            if not executor: continue
            try:
                result = executor(config, self.context, self.bot_id)
                results[node_id] = result
                if isinstance(result, dict):
                    for k, v in result.items():
                        self.context[f"{node_id}.{k}"] = v
                        self.context[k] = v
                self.execution_log.append({"node_id": node_id, "type": block_type, "status": "success", "result": result})
            except Exception as e:
                results[node_id] = {"error": str(e)}
                self.execution_log.append({"node_id": node_id, "type": block_type, "status": "error", "error": str(e)})
        elapsed = round(time.time() - start_time, 2)
        return {"status": "completed", "elapsed_seconds": elapsed, "results": results, "log": self.execution_log}

def run_flow(flow_data: dict, bot_id: str = None) -> dict:
    engine = FlowEngine(flow_data, bot_id=bot_id)
    return engine.execute()
