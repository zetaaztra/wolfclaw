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
    Sends the screenshots and captured inputs to GPT-4o for analysis.
    Returns a Flow JSON describing the automated steps.
    """
    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "openai library not installed. pip install openai"}

    api_key = get_key("openai")
    if not api_key:
        return {"error": "OpenAI API key is required for Vision Analysis."}

    client = OpenAI(api_key=api_key)
    
    macro_dir = Path.home() / "wolfclaw_macros" / session_id
    manifest_path = macro_dir / "manifest.json"
    
    if not manifest_path.exists():
        return {"error": f"Session {session_id} not found."}
        
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    actions = manifest.get("actions", [])
    if not actions:
        return {"error": "No actions recorded in this session."}
        
    # Build prompt and messages
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
    
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    
    user_content = [{"type": "text", "text": "Here is the recorded session sequence:"}]
    
    for idx, action in enumerate(actions[:10]):  # Limit to 10 to avoid token limits
        desc = action.get('description', '')
        user_content.append({"type": "text", "text": f"\nStep {idx+1}: {desc}"})
        
        img_name = action.get('image')
        if img_name:
            img_path = macro_dir / img_name
            if img_path.exists():
                base64_image = encode_image(str(img_path))
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "low"
                    }
                })
                
    user_content.append({"type": "text", "text": "\nPlease generate the JSON Flow representing this automation."})
    messages.append({"role": "user", "content": user_content})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=2000,
            temperature=0.2
        )
        
        result_text = response.choices[0].message.content
        if result_text.startswith("```json"):
            result_text = result_text[7:-3].strip()
            
        return json.loads(result_text)
    except Exception as e:
        return {"error": f"Vision analysis failed: {str(e)}"}
