"""
Phase 14 — Notification Center API Routes
"""
from fastapi import APIRouter
from core.notifications import notifications

router = APIRouter()

@router.get("/notifications")
async def get_notifications(limit: int = 50):
    return {
        "unread_count": notifications.get_unread_count(),
        "notifications": notifications.get_all(limit)
    }

@router.get("/notifications/count")
async def get_unread_count():
    return {"unread_count": notifications.get_unread_count()}

@router.post("/notifications/read-all")
async def mark_all_read():
    notifications.mark_all_read()
    return {"status": "all_read"}

@router.post("/notifications/{notif_id}/read")
async def mark_read(notif_id: int):
    notifications.mark_read(notif_id)
    return {"status": "read"}

@router.delete("/notifications")
async def clear_notifications():
    notifications.clear()
    return {"status": "cleared"}
