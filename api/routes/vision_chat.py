"""
Vision Chat — allows users to paste screenshots into chat for VLM analysis.
"""
import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.local_db import get_key_local
from auth.supabase_client import get_current_user

router = APIRouter()

class VisionRequest(BaseModel):
    image_base64: str
    prompt: str = "What do you see in this image? Analyze it."
    bot_id: str = ""

@router.post("/chat/vision")
async def vision_chat(req: VisionRequest):
    """Analyze a pasted screenshot using a Vision Language Model."""
    user = get_current_user()
    user_id = user["id"] if user else "local_user"

    # Try providers in order: OpenAI, Anthropic, Google
    providers = [
        ("openai", _call_openai_vision),
        ("anthropic", _call_anthropic_vision),
        ("google", _call_google_vision),
    ]

    for provider_name, call_fn in providers:
        api_key = get_key_local(user_id, f"{provider_name}_key")
        if api_key:
            try:
                result = call_fn(api_key, req.image_base64, req.prompt)
                return {"provider": provider_name, "analysis": result}
            except Exception as e:
                continue

    raise HTTPException(status_code=400, detail="No VLM-capable API key found. Add an OpenAI, Anthropic, or Google key in Settings.")


def _call_openai_vision(api_key: str, image_b64: str, prompt: str) -> str:
    import requests
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "gpt-4o",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                ]
            }],
            "max_tokens": 1000
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_anthropic_vision(api_key: str, image_b64: str, prompt: str) -> str:
    import requests
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        },
        json={
            "model": "claude-3-5-sonnet-20240620",
            "max_tokens": 1000,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                    {"type": "text", "text": prompt}
                ]
            }]
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def _call_google_vision(api_key: str, image_b64: str, prompt: str) -> str:
    import requests
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": image_b64}}
                ]
            }]
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
