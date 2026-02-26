import os
import sys
import subprocess
import time
from pathlib import Path
import paramiko

try:
    from core.integrations.google_workspace import read_emails, check_calendar
    from core.integrations.slack_connector import post_to_slack, read_slack_messages
except ImportError:
    pass

try:
    from core.plugins.plugin_manager import plugin_manager
except ImportError:
    plugin_manager = None

# Determine OS
_IS_WINDOWS = os.name == 'nt'
_OS_NAME = "Windows" if _IS_WINDOWS else "Ubuntu/Linux"

# Desktop specific directories
SCREENSHOT_DIR = Path.home() / "wolfclaw_screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# ----------- TOOL IMPLEMENTATIONS -----------

def run_remote_ssh_command(command: str, host: str = "", confidence_score: int = 100) -> str:
    """Executes a terminal command on an external server using saved SSH credentials."""
    target_host, port_str, user, password, key_content = host, "22", "ubuntu", "", ""
    
    # Ensure confidence_score is an integer
    try:
        score = int(confidence_score)
    except (ValueError, TypeError):
        score = 100

    if score < 90:
        return "SAFETY ABORT: Your confidence score is too low. DO NOT GUESS. Ask the user a clarifying question instead."

    try:
        from core.bot_manager import _get_active_workspace_id
        workspace_id = _get_active_workspace_id()
        if workspace_id and workspace_id != "00000000-0000-0000-0000-000000000000":
            if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
                from core import local_db
                ssh_list = local_db.get_workspace_ssh(workspace_id)
            else:
                from core.config import get_supabase
                res = get_supabase().table("workspaces").select("ssh_config").eq("id", workspace_id).execute()
                ssh_list = res.data[0].get("ssh_config") or []
            
            if isinstance(ssh_list, list) and len(ssh_list) > 0:
                # Find by host or default to first
                selected = None
                if target_host:
                    selected = next((s for s in ssh_list if s.get("host") == target_host), None)
                
                if not selected:
                    selected = ssh_list[0]
                
                target_host = selected.get("host", "")
                port_str = str(selected.get("port", "22"))
                user = selected.get("user", "ubuntu")
                password = selected.get("password", "")
                key_content = selected.get("key_content", "")
    except Exception:
        pass

    # Fallback to isolated env for isolated subprocess workers
    if not target_host:
        target_host = os.environ.get("WOLFCLAW_SSH_HOST", "")
        port_str = str(os.environ.get("WOLFCLAW_SSH_PORT", "22"))
        user = os.environ.get("WOLFCLAW_SSH_USER", "ubuntu")
        password = os.environ.get("WOLFCLAW_SSH_PASSWORD", "")
        key_content = os.environ.get("WOLFCLAW_SSH_KEY_CONTENT", "")

    if not target_host:
        return "Error: Remote server host is not configured. The user needs to add their Server IP in the 'Remote Servers' dashboard first."

    if not password and not key_content:
         return "Error: No SSH authentication method provided. The user needs to provide either a Password or a PEM key in the 'Remote Servers' dashboard."

    port = int(port_str) if str(port_str).isdigit() else 22

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if key_content:
            import io
            key_io = io.StringIO(key_content)
            key = paramiko.RSAKey.from_private_key(key_io)
            client.connect(hostname=target_host, port=port, username=user, pkey=key, timeout=10)
        else:
            client.connect(hostname=target_host, port=port, username=user, password=password, timeout=10)
        
        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        
        output = stdout.read().decode('utf-8')
        err_output = stderr.read().decode('utf-8')
        
        client.close()

        final_output = output
        if err_output:
            final_output += f"\nError Output:\n{err_output}"
            
        return final_output if final_output.strip() else "Remote command executed successfully with no output."
        
    except Exception as e:
        return f"Failed to execute command on remote server: {str(e)}"

def web_search(query: str) -> str:
    """Search the web and return top results."""
    try:
        from duckduckgo_search import DDGS
        
        results = []
        with DDGS() as ddgs:
            # Use 'keywords' instead of 'query'? No, .text() takes 'keywords'
            for r in ddgs.text(keywords=query, max_results=5):
                results.append(f"{r.get('title', 'No Title')}\n{r.get('body', r.get('snippet', ''))}\nURL: {r.get('href', r.get('link', ''))}")
        
        if not results:
            # Fallback to older API if needed, but ddgs.text() is the current official one
            return f"No results found for: {query}"
        
        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"Web search failed: {str(e)}"

def read_document(file_path: str) -> str:
    """Read text from a PDF or text file."""
    try:
        path = Path(file_path).expanduser().resolve()
        
        if not path.exists():
            return f"FILE NOT FOUND: The path '{path}' does not exist. Do not guess again. You must use the run_terminal_command tool with 'dir' or 'ls' to explore the file system and find the correct path before trying again."
        
        if path.suffix.lower() == '.pdf':
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                text = "\n\n".join([page.extract_text() or "" for page in reader.pages])
                # Truncate to prevent context window overflow
                if len(text) > 8000:
                    text = text[:8000] + "\n\n... [TRUNCATED — file is too large. Ask the user to specify which section they need.]"
                return text if text.strip() else "The PDF appears to be empty or contains only images (no extractable text)."
            except ImportError:
                return "Error: pypdf not installed. Run: pip install pypdf"
        
        elif path.suffix.lower() in ['.txt', '.md', '.py', '.js', '.json', '.csv', '.log', '.yaml', '.yml', '.ini', '.cfg', '.conf', '.sh', '.bat', '.ps1', '.html', '.css']:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
            if len(text) > 8000:
                text = text[:8000] + "\n\n... [TRUNCATED — file is too large.]"
            return text
        
        else:
            return f"Error: Unsupported file type '{path.suffix}'. Supported: .pdf, .txt, .md, .py, .js, .json, .csv, .log, .yaml, .html, .css, .sh, .bat, .ps1"
    
    except Exception as e:
        return f"Failed to read document: {str(e)}"

# ----------- DESKTOP-ONLY LOCAL TOOLS -----------

def _is_command_safe(command: str) -> bool:
    """Security check to prevent malicious command injection."""
    # List of dangerous characters that could be used for injection
    # We allow | for piping, && and ; for chaining, and > for redirection
    # as they are essential for agentic tasks.
    forbidden = ["`", "$( "]
    
    # Check for encoded versions or variations
    for f in forbidden:
        if f in command:
            return False
    
    # Block common destructive commands if they aren't part of a safe context
    destructive = ["rm -rf /", "format ", "mkfs ", "rd /s /q c:"]
    for d in destructive:
        if d in command.lower():
            return False
            
    return True

def run_terminal_command(command: str, confidence_score: int = 100) -> str:
    """Run a terminal command locally on the host machine."""
    
    # Measure Twice Safety Check
    if confidence_score < 90:
        return "SAFETY ABORT: Your confidence score is too low. DO NOT GUESS. Ask the user a clarifying question instead."
        
    if not _is_command_safe(command):
        return "SECURITY ABORT: The command contains potentially malicious characters or destructive operations. For your safety, I cannot execute this."

    try:
        if _IS_WINDOWS:
            result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, timeout=60)
        else:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, executable="/bin/bash", timeout=60)
        
        output = result.stdout
        err_output = result.stderr
        
        final_output = output
        if err_output:
            final_output += f"\nError Output:\n{err_output}"
            
        return final_output if final_output.strip() else "Command executed successfully with no output."
    except Exception as e:
        return f"Failed to execute command: {str(e)}"

def capture_screenshot() -> str:
    """Takes a screenshot of the user's screen and saves it."""
    try:
        from PIL import ImageGrab
        
        timestamp = int(time.time())
        filename = f"screenshot_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename
        
        img = ImageGrab.grab()
        img.save(str(filepath))
        
        return f"SCREENSHOT_CAPTURED:{filepath}"
    except ImportError:
        return "Error: Pillow library not installed. Run: pip install Pillow"
    except OSError:
        return "Error: No display available. Cannot take screenshots on a headless server (no monitor connected)."
    except Exception as e:
        return f"Failed to capture screenshot: {str(e)}"

def simulate_gui(action: str, keys: str = "", x: int = 0, y: int = 0) -> str:
    """Simulates keyboard typing, hotkeys, or mouse clicks using PyAutoGUI."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5

        if action == "type":
            if not keys: return "Error: No text provided to type."
            pyautogui.write(keys, interval=0.05)
            return f"Successfully typed: '{keys}'"
        elif action == "hotkey":
            if not keys: return "Error: No keys provided for hotkey."
            key_list = [k.strip() for k in keys.split(",")]
            pyautogui.hotkey(*key_list)
            return f"Successfully pressed hotkey: {keys}"
        elif action == "press":
            if not keys: return "Error: No key provided to press."
            pyautogui.press(keys)
            return f"Successfully pressed: {keys}"
        elif action == "click":
            pyautogui.click(x=x if x > 0 else None, y=y if y > 0 else None)
            return f"Successfully clicked at current mouse position (or {x},{y} if provided)."
        else:
            return f"Error: Unknown GUI action '{action}'. Use type, hotkey, press, or click."
    except ImportError:
        return "Error: pyautogui is not installed. Run: pip install pyautogui"
    except Exception as e:
        return f"GUI simulation failed: {str(e)}"

def web_browser(action: str, url: str = "") -> str:
    """Headless web browser actions using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
        
        if action == "extract_text":
            if not url: return "Error: No URL provided."
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                try:
                    page.goto(url, timeout=30000, wait_until="networkidle")
                    text = page.locator("body").inner_text()
                    title = page.title()
                except Exception as e:
                    browser.close()
                    return f"Failed to load {url}: {str(e)}"
                
                browser.close()
                if len(text) > 8000:
                    text = text[:8000] + "\n\n... [TRUNCATED]"
                return f"Title: {title}\nURL: {url}\n\nContent:\n{text}"
        else:
            return f"Error: Unknown browser action '{action}'."
    except ImportError:
        return "Error: playwright is not installed. Run: pip install playwright && playwright install chromium"
    except Exception as e:
        return f"Web browser task failed: {str(e)}"

# ----------- TOOL SCHEMAS (JSON) -----------

WOLFCLAW_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_remote_ssh_command",
            "description": "Run a command on the user's remote Linux server (AWS/VirtualBox) via SSH. ALWAYS use this if the user asks to manage a server, check remote logs, or do something on AWS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact bash command to execute on the remote linux machine (e.g. 'ls -la', 'docker ps', etc)."
                    },
                    "host": {
                        "type": "string",
                        "description": "Optional: The IP address or hostname of the specific server to target. Defaults to the first saved server."
                    },
                    "confidence_score": {
                        "type": "integer",
                        "description": "An integer from 1-100 reflecting how confident you are that this is the EXACT correct command and path. If below 90, the system will abort."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for real-time information. Use this when the user asks about current events, needs to look something up, or asks for information you don't have. Returns top 5 results with titles, snippets, and URLs. You MUST read the snippets carefully and verify they answer the user's specific question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the web."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_document",
            "description": "Read the contents of a document file (PDF, text, code, markdown, CSV, etc.). Use this when the user asks you to read, summarize, or analyze a file on their computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The full path to the file to read (e.g. '/path/to/report.pdf' or '~/documents/notes.txt')."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_emails",
            "description": "Read recent emails from the user's connected Gmail account.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "The maximum number of recent emails to read (default 5)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_calendar",
            "description": "Check the user's Google Calendar for upcoming events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "The number of days ahead to check (default 1)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "post_to_slack",
            "description": "Post a message to a specific Slack channel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {
                        "type": "string",
                        "description": "The Slack channel ID or name (e.g., '#general')."
                    },
                    "message": {
                        "type": "string",
                        "description": "The message text to post."
                    }
                },
                "required": ["channel", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_slack_messages",
            "description": "Read recent messages from a specific Slack channel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {
                        "type": "string",
                        "description": "The Slack channel ID or name (e.g., '#general')."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "The maximum number of messages to retrieve (default 5)."
                    }
                },
                "required": ["channel"]
            }
        }
    }
]

# Inject Desktop tools if environment allows it
if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
    WOLFCLAW_TOOLS.extend([
        {
            "type": "function",
            "function": {
                "name": "run_terminal_command",
                "description": f"Run a command on the user's LOCAL machine. The OS is {_OS_NAME}. {'Use POWERSHELL syntax only. To open GUI apps ALWAYS use `Start-Process code/chrome/notepad`. To close apps ALWAYS use `taskkill /IM chrome.exe /F` or `taskkill /IM WindowsCamera.exe /F`. To open the Windows Camera app use `start microsoft.windows.camera:`. Do not use `Start-Process` for CLI commands like `mkdir`.' if _IS_WINDOWS else 'Use bash syntax.'} ALWAYS run the command.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The exact command to execute."
                        },
                        "confidence_score": {
                            "type": "integer",
                            "description": "An integer from 1-100 reflecting how confident you are. NEVER guess paths. Use 99 if you are certain."
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "capture_screenshot",
                "description": "Take a screenshot of the user's screen. ONLY use this tool when the user EXPLICITLY asks.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "simulate_gui",
                "description": "Simulate human keyboard and mouse inputs. ONLY use this when the user EXPLICITLY asks you to type out a specific phrase, press a key, or click. Do NOT use this to talk to the user. Do NOT use this to write long blocks of code (use run_terminal_command with Out-File instead).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["type", "hotkey", "press", "click"]},
                        "keys": {"type": "string", "description": "Text to type or keys to press/hotkey separated by commas. If typing code, you must handle all newlines and indents perfectly."},
                        "x": {"type": "integer"},
                        "y": {"type": "integer"}
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "web_browser",
                "description": "Interact with web pages directly using a headless Chrome browser.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["extract_text"]},
                        "url": {"type": "string"}
                    },
                    "required": ["action", "url"]
                }
            }
        }
    ])

# ----------- TOOL ROUTER -----------

if plugin_manager:
    WOLFCLAW_TOOLS.extend(plugin_manager.get_all_tool_schemas())

def execute_tool(tool_name: str, arguments: dict) -> str:
    """Routes a tool call from the LLM to the matching python function."""
    if plugin_manager:
        plugin_res = plugin_manager.execute_tool(tool_name, arguments)
        if plugin_res is not None:
            return plugin_res

    if tool_name == "run_remote_ssh_command":
        return run_remote_ssh_command(
            arguments.get("command", ""),
            host=arguments.get("host", ""),
            confidence_score=arguments.get("confidence_score", 100)
        )
    elif tool_name == "web_search":
        return web_search(arguments.get("query", ""))
    elif tool_name == "read_document":
        return read_document(arguments.get("file_path", ""))
    elif tool_name == "read_emails":
        return read_emails(arguments.get("max_results", 5))
    elif tool_name == "check_calendar":
        return check_calendar(arguments.get("days", 1))
    elif tool_name == "post_to_slack":
        return post_to_slack(arguments.get("channel", ""), arguments.get("message", ""))
    elif tool_name == "read_slack_messages":
        return read_slack_messages(arguments.get("channel", ""), arguments.get("limit", 5))
    
    # Desktop tools
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        if tool_name == "run_terminal_command":
            return run_terminal_command(arguments.get("command", ""))
        elif tool_name == "capture_screenshot":
            return capture_screenshot()
        elif tool_name == "simulate_gui":
            return simulate_gui(
                arguments.get("action", ""),
                arguments.get("keys", ""),
                arguments.get("x", 0),
                arguments.get("y", 0)
            )
        elif tool_name == "web_browser":
            return web_browser(arguments.get("action", ""), arguments.get("url", ""))
    
    return f"Error: Tool '{tool_name}' is not recognized or has been disabled by security policy."
