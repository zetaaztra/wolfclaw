from fastapi import APIRouter
from core.activity_feed import activity_feed

router = APIRouter()

@router.get("/activity")
async def get_activity(limit: int = 50):
    """Return recent system activity events."""
    return {"events": activity_feed.get_recent(limit)}
