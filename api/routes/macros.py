from fastapi import APIRouter, HTTPException
from core.macro_recorder import recorder
from core.vision_analyzer import analyze_macro_session

router = APIRouter()

@router.post("/start")
async def start_macro_recording():
    """Start recording mouse and keyboard inputs + screenshots."""
    try:
        res = recorder.start_recording()
        return {"status": "success", "message": res, "session_id": recorder.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_macro_recording():
    """Stop recording."""
    try:
        session_id = recorder.session_id
        res = recorder.stop_recording()
        return {"status": "success", "message": res, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/analyze")
async def analyze_macro(session_id: str):
    """Send recorded session to an LLM Vision model to generate a Flow JSON."""
    result = analyze_macro_session(session_id)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return {"status": "success", "flow_data": result}
