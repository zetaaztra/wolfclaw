import os
import json
import base64
from pathlib import Path
from core.config import get_key

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_macro_session(session_id: str):
    """
    Sends the screenshots and captured inputs to an LLM Vision model (GPT-4o, Claude 3.5, or Gemini) for analysis.
    Returns a Flow JSON describing the automated steps.
    """
    macro_dir = Path.home() / "wolfclaw_macros" / session_id
    manifest_path = macro_dir / "manifest.json"
    
    if not manifest_path.exists():
        return {"error": f"Session {session_id} not found."}
        
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    actions = manifest.get("actions", [])
    if not actions:
        return {"error": "No actions recorded in this session."}

    # System Prompt
    system_prompt = """
You are an expert Automation Engineer. You have been provided with a series of screenshots and user actions (clicks, keypresses) from a recorded session.
Your job is to translate this recorded workflow into a Wolfclaw Flow JSON structure.

Output MUST be valid JSON (with no markdown wrappers) following this Flow format:
{
  "name": "Auto-Generated Macro",
  "description": "...",
  "flow_data": {
    "nodes": {
      "node_1": { "type": "simulate_gui", "config": { "action": "type", "keys": "..." } },
      "node_2": { "type": "simulate_gui", "config": { "action": "click", "x": 100, "y": 200 } }
    },
    "edges": [
      { "from": "node_1", "to": "node_2" }
    ]
  }
}
Combine redundant clicks or types into clean steps. Use "action": "type" and "keys" for keyboard. Use "action": "click" and "x", "y" for mouse.
Use "action": "hotkey" and "keys": "ctrl,c" for hotkeys.
"""

    # --- PROVIDER SELECTION ---
    openai_key = get_key("openai")
    anthropic_key = get_key("anthropic")
    google_key = get_key("google")
    nvidia_key = get_key("nvidia")

    if anthropic_key:
        return _analyze_with_anthropic(anthropic_key, system_prompt, macro_dir, actions)
    elif nvidia_key:
        return _analyze_with_nvidia(nvidia_key, system_prompt, macro_dir, actions)
    elif openai_key:
        return _analyze_with_openai(openai_key, system_prompt, macro_dir, actions)
    elif google_key:
         return _analyze_with_google(google_key, system_prompt, macro_dir, actions)
    else:
        return {"error": "Vision analysis requires an API key (Anthropic, Nvidia, OpenAI, or Google). Please add one in Settings."}

def _analyze_with_openai(api_key, system_prompt, macro_dir, actions):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        messages = [{"role": "system", "content": system_prompt}]
        user_content = [{"type": "text", "text": "Represent this session as a Wolfclaw Flow JSON:"}]
        
        for idx, action in enumerate(actions[:10]):
            desc = action.get('description', '')
            user_content.append({"type": "text", "text": f"\nStep {idx+1}: {desc}"})
            img_name = action.get('image')
            if img_name:
                img_path = macro_dir / img_name
                if img_path.exists():
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encode_image(str(img_path))}", "detail": "low"}
                    })
        
        messages.append({"role": "user", "content": user_content})
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=2000,
            temperature=0.2
        )
        return _parse_json_res(response.choices[0].message.content)
    except Exception as e:
        return {"error": f"OpenAI Vision failed: {str(e)}"}

def _analyze_with_anthropic(api_key, system_prompt, macro_dir, actions):
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        content = []
        for idx, action in enumerate(actions[:10]):
            desc = action.get('description', '')
            content.append({"type": "text", "text": f"Step {idx+1}: {desc}"})
            img_name = action.get('image')
            if img_name:
                img_path = macro_dir / img_name
                if img_path.exists():
                     with open(img_path, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")
                     content.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": data}
                     })
        
        content.append({"type": "text", "text": "Generate the Wolfclaw Flow JSON."})
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": content}]
        )
        return _parse_json_res(message.content[0].text)
    except Exception as e:
        return {"error": f"Anthropic Vision failed: {str(e)}"}

def _analyze_with_google(api_key, system_prompt, macro_dir, actions):
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        parts = [system_prompt, "Represent this session as a Wolfclaw Flow JSON:\n"]
        for idx, action in enumerate(actions[:10]):
            desc = action.get('description', '')
            parts.append(f"Step {idx+1}: {desc}")
            img_name = action.get('image')
            if img_name:
                img_path = macro_dir / img_name
                if img_path.exists():
                    with open(img_path, "rb") as f:
                        parts.append({"mime_type": "image/png", "data": f.read()})
        
        response = model.generate_content(parts)
        return _parse_json_res(response.text)
    except Exception as e:
        return {"error": f"Google Vision failed: {str(e)}"}

def _analyze_with_nvidia(api_key, system_prompt, macro_dir, actions):
    """Nvidia NIM VLM Support (OpenAI-compatible)"""
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        
        # NIM often works best with specific model names. We'll use a standard one.
        # Note: In a production environment, this should be configurable.
        model_name = "nvidia/neva-22b" 
        
        messages = [{"role": "system", "content": system_prompt}]
        user_content = [{"type": "text", "text": "Represent this session as a Wolfclaw Flow JSON:"}]
        
        for idx, action in enumerate(actions[:10]):
            desc = action.get('description', '')
            user_content.append({"type": "text", "text": f"\nStep {idx+1}: {desc}"})
            img_name = action.get('image')
            if img_name:
                img_path = macro_dir / img_name
                if img_path.exists():
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encode_image(str(img_path))}"}
                    })
        
        messages.append({"role": "user", "content": user_content})
        
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=2000,
            temperature=0.2
        )
        return _parse_json_res(response.choices[0].message.content)
    except Exception as e:
        return {"error": f"Nvidia Vision failed: {str(e)}"}

def _parse_json_res(text):
    try:
        if text.startswith("```json"):
            text = text[7:-3].strip()
        return json.loads(text)
    except Exception as e:
        return {"error": f"Failed to parse model response: {str(e)}"}
