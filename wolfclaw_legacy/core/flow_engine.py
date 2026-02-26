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

logger = logging.getLogger(__name__)

# ─────────── BLOCK REGISTRY ───────────
# Maps block type strings to executor functions.
# Each executor receives (config: dict, context: dict) and returns a result.

def _exec_manual_trigger(config: dict, context: dict) -> dict:
    """Manual trigger — just passes through. Used to start a flow on-demand."""
    return {"triggered": True, "timestamp": datetime.now().isoformat()}


def _exec_schedule_trigger(config: dict, context: dict) -> dict:
    """Schedule trigger — stores cron expression. Actual scheduling is handled by the scheduler."""
    return {"cron": config.get("cron", ""), "scheduled": True}


def _exec_ai_prompt(config: dict, context: dict) -> dict:
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
    
    try:
        response = engine.chat(messages, system_prompt=system, stream=False)
        reply = response.choices[0].message.content
        return {"response": reply}
    except Exception as e:
        return {"error": str(e)}


def _exec_terminal_command(config: dict, context: dict) -> dict:
    """Execute a local terminal command."""
    from core.tools import run_terminal_command
    command = config.get("command", "")
    # Resolve template variables
    for key, value in context.items():
        command = command.replace(f"{{{{{key}}}}}", str(value))
    
    result = run_terminal_command(command)
    return {"output": result}


def _exec_web_search(config: dict, context: dict) -> dict:
    """Run a web search query."""
    from core.tools import web_search as web_search_tool
    query = config.get("query", "")
    for key, value in context.items():
        query = query.replace(f"{{{{{key}}}}}", str(value))
    
    result = web_search_tool(query)
    return {"results": result}


def _exec_condition(config: dict, context: dict) -> dict:
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


def _exec_output(config: dict, context: dict) -> dict:
    """Output block — formats and returns the final result."""
    template = config.get("message", "Flow completed.")
    for key, value in context.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    
    return {"message": template}


def _exec_screenshot(config: dict, context: dict) -> dict:
    """Take a screenshot of the current screen."""
    from core.tools import capture_screenshot
    result = capture_screenshot()
    return {"screenshot": result}


def _exec_http_request(config: dict, context: dict) -> dict:
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
    
    try:
        if method == "GET":
            resp = req_lib.get(url, headers=headers, timeout=30)
        elif method == "POST":
            resp = req_lib.post(url, headers=headers, data=body, timeout=30)
        elif method == "PUT":
            resp = req_lib.put(url, headers=headers, data=body, timeout=30)
        elif method == "DELETE":
            resp = req_lib.delete(url, headers=headers, timeout=30)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        return {"status_code": resp.status_code, "body": resp.text[:5000]}
    except Exception as e:
        return {"error": str(e)}


def _exec_delay(config: dict, context: dict) -> dict:
    """Wait for a specified number of seconds."""
    seconds = config.get("seconds", 1)
    time.sleep(min(seconds, 300))  # Cap at 5 minutes
    return {"waited": seconds}


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
]


# ─────────── FLOW ENGINE ───────────

class FlowEngine:
    """
    Executes a flow defined as a JSON graph.
    
    Flow JSON format:
    {
        "nodes": {
            "node_1": {"type": "manual_trigger", "config": {}, "position": {"x": 100, "y": 100}},
            "node_2": {"type": "ai_prompt", "config": {"model": "gpt-4o", "prompt": "..."}, "position": {"x": 300, "y": 100}},
            ...
        },
        "edges": [
            {"from": "node_1", "to": "node_2"},
            ...
        ]
    }
    """
    
    def __init__(self, flow_data: dict):
        self.nodes = flow_data.get("nodes", {})
        self.edges = flow_data.get("edges", [])
        self.context: Dict[str, Any] = {}
        self.execution_log: List[dict] = []
    
    def _topological_sort(self) -> List[str]:
        """Sort nodes in execution order using Kahn's algorithm."""
        in_degree = {nid: 0 for nid in self.nodes}
        adjacency = {nid: [] for nid in self.nodes}
        
        for edge in self.edges:
            src, dst = edge["from"], edge["to"]
            if src in adjacency and dst in in_degree:
                adjacency[src].append(dst)
                in_degree[dst] += 1
        
        # Start with nodes that have no incoming edges
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []
        
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If not all nodes are processed, there's a cycle
        if len(order) != len(self.nodes):
            logger.warning("Cycle detected in flow graph. Executing reachable nodes only.")
        
        return order
    
    def execute(self) -> dict:
        """Execute the entire flow and return results."""
        start_time = time.time()
        order = self._topological_sort()
        
        results = {}
        
        for node_id in order:
            node = self.nodes.get(node_id, {})
            block_type = node.get("type", "")
            config = node.get("config", {})
            
            executor = BLOCK_EXECUTORS.get(block_type)
            if not executor:
                logger.warning(f"Unknown block type: {block_type}")
                self.execution_log.append({
                    "node_id": node_id, "type": block_type,
                    "status": "skipped", "reason": "Unknown block type"
                })
                continue
            
            try:
                # Execute the block
                result = executor(config, self.context)
                results[node_id] = result
                
                # Merge result into context for downstream blocks
                if isinstance(result, dict):
                    for k, v in result.items():
                        self.context[f"{node_id}.{k}"] = v
                        # Also set shorthand (last node's output accessible by key name)
                        self.context[k] = v
                
                self.execution_log.append({
                    "node_id": node_id, "type": block_type,
                    "status": "success", "result": _safe_serialize(result)
                })
                
                # Handle condition branching
                if block_type == "condition" and isinstance(result, dict):
                    branch = result.get("branch", "true")
                    # Filter edges: only follow the matching branch output
                    # Convention: output_0 = true branch, output_1 = false branch
                    # For simplicity, we don't skip nodes — condition result is in context

            except Exception as e:
                logger.error(f"Block {node_id} ({block_type}) failed: {e}")
                results[node_id] = {"error": str(e)}
                self.execution_log.append({
                    "node_id": node_id, "type": block_type,
                    "status": "error", "error": str(e)
                })
        
        elapsed = round(time.time() - start_time, 2)
        
        return {
            "status": "completed",
            "elapsed_seconds": elapsed,
            "results": results,
            "log": self.execution_log,
            "final_context": {k: _safe_serialize(v) for k, v in self.context.items()}
        }


def _safe_serialize(value: Any) -> Any:
    """Ensure a value is JSON-serializable."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, dict):
        return {k: _safe_serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_serialize(v) for v in value]
    return str(value)


def run_flow(flow_data: dict) -> dict:
    """Convenience function to execute a flow from its JSON data."""
    engine = FlowEngine(flow_data)
    return engine.execute()
