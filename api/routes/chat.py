from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import os

from core.llm_engine import WolfEngine
from core import bot_manager
from api.deps import get_current_user

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class ChatRequest(BaseModel):
    bot_id: str
    messages: List[ChatMessage]
    doc_id: Optional[str] = None
    chat_id: Optional[str] = None

class WarRoomRequest(BaseModel):
    manager_bot_id: str
    sub_bot_ids: List[str]
    messages: List[ChatMessage]
    chat_id: Optional[str] = None

@router.post("/send")
async def send_message(req: ChatRequest, user: dict = Depends(get_current_user)):
    """Send a chat message, get AI response with tool support"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    try:
        bots = bot_manager.get_bots(user_id=user["id"])
        if req.bot_id not in bots:
             raise HTTPException(status_code=404, detail="Bot not found.")

        bot = bots[req.bot_id]
        
        # Convert pydantic messages to dicts
        messages = [m.dict() for m in req.messages]
        
        # Determine the final system prompt with document context
        system_prompt = bot["prompt"]
        if req.doc_id:
            from core import local_db
            doc_content = local_db.get_document_content(req.doc_id)
            if doc_content:
                system_prompt = f"The user has uploaded a document for context.\n\n<document_context>\n{doc_content}\n</document_context>\n\n" + system_prompt
        
        # --- PHASE 13: Knowledge Base (RAG) Auto-Context Injection ---
        try:
            from core import local_db as _db
            from core.rag_engine import search_chunks, format_context_for_prompt
            
            # Get the user's latest message as the search query
            user_query = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_query = m.get("content", "")
                    break
            
            if user_query:
                all_chunks = _db.get_knowledge_chunks_for_bot(req.bot_id)
                if all_chunks:
                    relevant = search_chunks(user_query, all_chunks, top_k=5)
                    if relevant:
                        kb_context = format_context_for_prompt(relevant)
                        if kb_context:
                            system_prompt = system_prompt + "\n\n" + kb_context
        except Exception as kb_err:
            import logging
            logging.getLogger(__name__).warning(f"KB injection failed: {kb_err}")
        
        # Initialize the engine with the bot's model and fallbacks
        engine = WolfEngine(
            bot["model"],
            fallback_models=bot.get("fallback_models", [])
        )
        
        # Call the engine
        response = engine.chat(
            messages=messages,
            system_prompt=system_prompt,
            bot_id=req.bot_id
        )
        
        reply = response.choices[0].message.content
        
        # If AI reply is empty, build summary from tool results
        if not reply or not reply.strip():
            tool_results = []
            for msg in messages:
                if msg.get("role") == "tool" and msg.get("content"):
                    tool_results.append(msg["content"])
            if tool_results:
                reply = "Here's what I found:\n\n```\n" + "\n".join(tool_results)[:3000] + "\n```"
            else:
                reply = "*(Task completed)*"
        
        # Collect any tool messages that were appended during execution
        new_tool_messages = []
        original_count = len(req.messages)
        for msg in messages[original_count:]:
            if msg.get("role") == "tool":
                new_tool_messages.append({
                    "name": msg.get("name", "Tool"),
                    "content": msg.get("content", "")
                })
        
        # --- PHASE 11: Auto-save Chat History ---
        from core import local_db
        import json
        ws_id = bot_manager._get_active_workspace_id()
        
        # The title is just the first user message (truncated if needed)
        title = "New Chat"
        for m in messages:
            if m.get("role") == "user":
                title = m["content"][:40] + ("..." if len(m["content"]) > 40 else "")
                break
                
        # We must append the NEW assistant reply before saving
        final_history_messages = messages.copy()
        final_history_messages.append({"role": "assistant", "content": reply})
        messages_json = json.dumps(final_history_messages)
        
        new_chat_id = local_db.save_chat_history(
            ws_id=ws_id, 
            bot_id=req.bot_id, 
            title=title, 
            messages=messages_json, 
            chat_id=req.chat_id
        )
        
        return {
            "status": "success",
            "reply": reply,
            "tool_messages": new_tool_messages,
            "chat_id": new_chat_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/warroom/send")
async def send_warroom_message(req: WarRoomRequest):
    """Executes a multi-agent orchestrated chat sequence."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    try:
        from core.orchestrator import MultiAgentOrchestrator
        
        orchestrator = MultiAgentOrchestrator(
            manager_bot_id=req.manager_bot_id,
            sub_bot_ids=req.sub_bot_ids
        )
        
        # Get the latest user prompt
        messages = [m.dict() for m in req.messages]
        user_prompt = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_prompt = m.get("content", "")
                break
                
        # Run the orchestration sequence
        events = orchestrator.run_war_room(user_prompt, messages[:-1]) # exclude the last user prompt as it's passed explicitly
        
        return {
            "status": "success",
            "events": events
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bots")
async def list_chat_bots():
    """List bots available for chatting"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    try:
        bots = bot_manager.get_bots()
        bot_list = []
        for b_id, b_data in bots.items():
            bot_list.append({
                "id": b_id,
                "name": b_data["name"],
                "model": b_data["model"]
            })
        return {"status": "success", "bots": bot_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import FileResponse
from pathlib import Path

@router.get("/media")
async def get_media(path: str):
    """Serve a local image to the frontend (restricted to Wolfclaw screenshots dir)"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
    
    try:
        req_path = Path(path).resolve()
        screenshot_dir = (Path.home() / "wolfclaw_screenshots").resolve()
        
        # Security check: ensure the requested file is inside our screenshot dir
        if not str(req_path).startswith(str(screenshot_dir)):
            raise HTTPException(status_code=403, detail="Access denied. Can only serve files from the official screenshot directory.")
            
        if not req_path.exists():
            raise HTTPException(status_code=404, detail="File not found.")
            
        return FileResponse(str(req_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
