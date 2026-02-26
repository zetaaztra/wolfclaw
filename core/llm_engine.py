import os
import re
import json
import platform
import logging
from litellm import completion
from .config import get_key
from .tools import WOLFCLAW_TOOLS, execute_tool

logger = logging.getLogger(__name__)

# Ref: PAM-Sovereign-Orchestration

class WolfEngine:
    """
    Unified LLM router based on LiteLLM.
    Supports local Ollama, Nvidia, OpenAI, Anthropic, DeepSeek, etc.
    Automatically detects local Ollama instances.
    """

    def __init__(self, model_name: str, fallback_models: list = None):
        self.model_name = self._detect_local_model(model_name)
        self.fallback_models = fallback_models or []

    def _detect_local_model(self, model_name: str) -> str:
        """
        Check if Ollama is running locally. If so, and if the user hasn't 
        provided a specific cloud model (like gpt-4o), prioritize local.
        """
        # If user explicitly requested a cloud model, trust them
        cloud_prefixes = ["gpt-", "claude-", "gemini-", "nvidia/", "anthropic/", "openai/"]
        if any(model_name.lower().startswith(p) for p in cloud_prefixes):
            return model_name

        try:
            import requests
            # Check for Ollama
            response = requests.get("http://localhost:11434/api/tags", timeout=1)
            if response.status_code == 200:
                print("INFO: Local AI (Ollama) detected. Defaulting to local model.")
                # If model_name is generic like 'auto', use a default local one
                if model_name in ["auto", "default"]:
                    return "ollama/llama3"
                return model_name
        except:
            pass
        
        return model_name



    # ----------- SOUL.md / MEMORY / USER CONTEXT LOADING -----------

    def _load_global_soul(self) -> str:
        """Load and filter the global SOUL.md based on OS."""
        soul_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SOUL.md"),
            os.path.join(os.getcwd(), "SOUL.md"),
        ]
        for soul_path in soul_paths:
            if os.path.exists(soul_path):
                try:
                    with open(soul_path, "r", encoding="utf-8") as f:
                        raw_soul = f.read()
                    
                    is_windows = platform.system() == "Windows"
                    if is_windows:
                        raw_soul = re.sub(r'\[LINUX_ONLY_START\].*?\[LINUX_ONLY_END\]', '', raw_soul, flags=re.DOTALL)
                        raw_soul = raw_soul.replace("[WINDOWS_ONLY_START]", "").replace("[WINDOWS_ONLY_END]", "")
                    else:
                        raw_soul = re.sub(r'\[WINDOWS_ONLY_START\].*?\[WINDOWS_ONLY_END\]', '', raw_soul, flags=re.DOTALL)
                        raw_soul = raw_soul.replace("[LINUX_ONLY_START]", "").replace("[LINUX_ONLY_END]", "")
                    
                    return raw_soul.strip()
                except:
                    pass
        return ""

    def _load_bot_context(self, bot_id: str = None) -> str:
        """Load per-bot SOUL.md, USER.md, and MEMORY.md from workspace."""
        if not bot_id:
            return ""
        
        try:
            from .bot_manager import read_workspace_file
            
            parts = []
            
            # Per-bot personality
            bot_soul = read_workspace_file(bot_id, "SOUL.md")
            if bot_soul:
                parts.append(f"## YOUR PERSONAL IDENTITY\n{bot_soul}")
            
            # User profile
            user_md = read_workspace_file(bot_id, "USER.md")
            if user_md and user_md.strip() != "":
                parts.append(f"## OWNER PROFILE\n{user_md}")
            
            # Long-term memory
            memory_md = read_workspace_file(bot_id, "MEMORY.md")
            if memory_md and memory_md.strip() != "":
                parts.append(f"## YOUR LONG-TERM MEMORY\n{memory_md}")
            
            return "\n\n".join(parts)
        except:
            return ""

    # ----------- MODEL ROUTING -----------

    def _build_completion_kwargs(self, model: str, full_messages: list, stream: bool = False) -> dict:
        """Build the completion kwargs dict for a specific model."""
        kwargs = {
            "messages": full_messages,
            "stream": stream,
            "tools": WOLFCLAW_TOOLS
        }

        if model.startswith("nvidia/") or model.startswith("meta/"):
            # Strip 'nvidia/' if present to get the actual model name or just use the meta/ one
            actual_model = model.replace("nvidia/", "")
            if "llama" in actual_model and "/" not in actual_model:
                actual_model = f"meta/{actual_model}"
            kwargs["model"] = f"nvidia_nim/{actual_model}"
            key = get_key("nvidia")
            kwargs["api_key"] = key
            os.environ["NVIDIA_NIM_API_KEY"] = key
            kwargs["parallel_tool_calls"] = False
        elif model.startswith("deepseek/"):
            actual_model = model.replace("deepseek/", "")
            kwargs["model"] = f"openai/{actual_model}"
            kwargs["api_base"] = "https://api.deepseek.com/v1"
            key = get_key("deepseek")
            kwargs["api_key"] = key
            os.environ["DEEPSEEK_API_KEY"] = key

        else:
            kwargs["model"] = model
            if model.startswith("gpt"):
                key = get_key("openai")
                kwargs["api_key"] = key
                os.environ["OPENAI_API_KEY"] = key
            elif model.startswith("claude"):
                key = get_key("anthropic")
                kwargs["api_key"] = key
                os.environ["ANTHROPIC_API_KEY"] = key
            elif model.startswith("gemini"):
                key = get_key("google")
                kwargs["api_key"] = key
                os.environ["GEMINI_API_KEY"] = key
            elif model.startswith("ollama"):
                # Ollama runs locally, no key needed usually, just default base url.
                pass

        return kwargs

    # ----------- MEMORY REFLECTION -----------

    def _reflect_to_memory(self, bot_id: str, messages: list):
        """After a conversation turn, extract and save new facts to MEMORY.md."""
        if not bot_id:
            return
        
        try:
            from .bot_manager import read_workspace_file, write_workspace_file
            
            current_memory = read_workspace_file(bot_id, "MEMORY.md")
            
            # Build a small summary of just the last exchange
            recent = messages[-4:] if len(messages) > 4 else messages
            recent_text = "\n".join([f"{m.get('role','?')}: {m.get('content','')[:200]}" for m in recent if m.get('content')])
            
            # Use the LLM itself to extract facts (cheap, fast call)
            reflection_prompt = [
                {"role": "system", "content": 
                    "You are a memory manager. Read the conversation below and extract ONLY new important facts. "
                    "Output ONLY bullet points to append to memory. If nothing important, output 'NO_NEW_FACTS'. "
                    "Be very selective — only save things the user would want remembered long-term."
                },
                {"role": "user", "content": f"Current memory:\n{current_memory[:1000]}\n\nRecent conversation:\n{recent_text}"}
            ]
            
            kwargs = self._build_completion_kwargs(self.model_name, reflection_prompt)
            kwargs.pop("tools", None)  # No tools needed for reflection
            
            response = completion(**kwargs)
            new_facts = response.choices[0].message.content
            
            if new_facts and "NO_NEW_FACTS" not in new_facts:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                updated_memory = current_memory.rstrip() + f"\n\n## Session: {timestamp}\n{new_facts}\n"
                write_workspace_file(bot_id, "MEMORY.md", updated_memory)
                logger.info(f"Memory updated for bot {bot_id}")
        except Exception as e:
            logger.warning(f"Memory reflection failed (non-critical): {e}")

    # ----------- MAIN CHAT METHOD -----------

    def chat(self, messages: list, system_prompt: str = None, stream: bool = False, bot_id: str = None):
        """
        Send a chat request with multi-model fallback.
        messages: list of dicts [{"role": "user", "content": "..."}]
        bot_id: optional, used to load per-bot context and save memory
        """
        full_messages = []
        system_parts = []
        
        # Build comprehensive system prompt
        # 1. Global Soul (Base Directives)
        global_soul = self._load_global_soul()
        if global_soul:
            system_parts.append(f"# CORE DIRECTIVES\n{global_soul}")

        # 2. External Context (RAG, documents) - passed via system_prompt argument
        if system_prompt:
            system_parts.append(f"# EXTERNAL CONTEXT\n{system_prompt}")

        # 3. Personal Identity & Long-Term Context (Bot SOUL, User Context, Memory)
        bot_context = self._load_bot_context(bot_id)
        if bot_context:
            system_parts.append(bot_context)

        if system_parts:
            # Join with clear headers to help the LLM navigate the components
            full_messages.append({"role": "system", "content": "\n\n".join(system_parts)})
            
        full_messages.extend(messages)

        # Try primary model, then fallbacks
        models_to_try = [self.model_name] + self.fallback_models
        last_error = None
        response = None
        
        for i, model in enumerate(models_to_try):
            retries = 3
            while retries > 0:
                try:
                    if i > 0 or retries < 3:
                        logger.info(f"Attempting model: {model} (Retry: {3-retries})")
                    
                    kwargs = self._build_completion_kwargs(model, full_messages, stream)
                    response = completion(**kwargs)
                    break # Success!
                except Exception as e:
                    retries -= 1
                    last_error = e
                    if retries == 0:
                        logger.warning(f"Model {model} failed all retries: {e}")
                    else:
                        import time
                        time.sleep(1) # Brief pause before retry
                        continue
            
            if response:
                try:
                    # --- AGENTIC TOOL EXECUTION LOOP ---
                    max_loops = 10
                    loop_count = 0
                    while getattr(response.choices[0].message, "tool_calls", None) and loop_count < max_loops:
                        loop_count += 1
                        
                        assist_msg = response.choices[0].message
                        message_dict = {
                            "role": "assistant",
                            "content": assist_msg.content,
                            "tool_calls": [t.model_dump() for t in assist_msg.tool_calls]
                        }
                        
                        full_messages.append(message_dict)
                        messages.append(message_dict)
                        
                        for tool_call in response.choices[0].message.tool_calls:
                            function_name = tool_call.function.name
                            try:
                                function_args = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError:
                                function_args = {}
                            
                            print(f"INFO: AI called tool: {function_name} ({function_args})")
                            tool_result = execute_tool(function_name, function_args)
                            
                            tool_msg = {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": function_name,
                                "content": str(tool_result)
                            }
                            full_messages.append(tool_msg)
                            messages.append(tool_msg)
                        
                        kwargs["messages"] = full_messages
                        response = completion(**kwargs)
                    # --- END TOOL LOOP ---
                    
                    # Memory reflection (async-safe, non-blocking)
                    if bot_id:
                        try:
                            self._reflect_to_memory(bot_id, messages)
                        except:
                            pass  # Never let memory reflection crash the main flow
                    
                    # --- PHASE 17: Usage Analytics Logging ---
                    try:
                        import time as _time_mod
                        from core import local_db as _usage_db
                        from core.bot_manager import _get_active_workspace_id

                        ws_id = _get_active_workspace_id()
                        usage = getattr(response, 'usage', None)
                        prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
                        completion_tokens = getattr(usage, 'completion_tokens', 0) or 0
                        total_tokens = getattr(usage, 'total_tokens', 0) or (prompt_tokens + completion_tokens)

                        # Rough cost estimation (per 1M tokens)
                        COST_MAP = {
                            'gpt-4o': {'input': 2.50, 'output': 10.00},
                            'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
                            'claude-3-5-sonnet': {'input': 3.00, 'output': 15.00},
                            'llama': {'input': 0.50, 'output': 0.50},
                        }
                        cost_rate = {'input': 0.50, 'output': 0.50}  # default
                        for key, rate in COST_MAP.items():
                            if key in model.lower():
                                cost_rate = rate
                                break
                        
                        estimated_cost = (prompt_tokens * cost_rate['input'] / 1_000_000) + \
                                         (completion_tokens * cost_rate['output'] / 1_000_000)

                        _usage_db.log_usage(
                            ws_id=ws_id,
                            bot_id=bot_id or "",
                            model=model,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=total_tokens,
                            estimated_cost=round(estimated_cost, 6),
                            response_time_ms=0
                        )
                    except Exception as usage_err:
                        logger.warning(f"Usage logging failed (non-critical): {usage_err}")
                    
                    return response
                except Exception as e:
                    last_error = e
                    logger.warning(f"Error processing response from {model}: {e}")
                    # If this failed, we might still want to try the next model if possible, 
                    # but usually, if response was received it's a logic error here.
                    continue
                
        
        # All models failed
        raise RuntimeError(f"All models failed. Last error ({models_to_try[-1]}): {str(last_error)}")
