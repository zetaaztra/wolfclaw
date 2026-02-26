from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core import local_db
import os

security = HTTPBearer(auto_error=False)

async def get_current_user(auth: HTTPAuthorizationCredentials = Security(security)):
    """
    FastAPI dependency to get the current user from the session token.
    Supports both Desktop (Local DB) and Environment-fallbacks.
    """
    if os.environ.get("WOLFCLAW_ENVIRONMENT") == "desktop":
        if not auth or not auth.credentials:
            owner_id = os.environ.get("WOLFCLAW_OWNER_ID", "00000000-0000-0000-0000-000000000000")
            print(f"[AUTH] No Bearer token found. Falling back to dummy OwnerID: {owner_id}")
            return {"id": owner_id}
            
        token_prefix = auth.credentials[:8]
        print(f"[AUTH] Resolving session for token: {token_prefix}...")
        session = local_db.get_session(auth.credentials)
        
        if not session:
            print(f"[AUTH] FAILED: Invalid or expired session token: {token_prefix}...")
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        user_id = session["user_id"]
        print(f"[AUTH] SUCCESS: Resolved UserID: {user_id}")
        return {"id": user_id}
        
    # Cloud mode fallback
    fallback_id = "00000000-0000-0000-0000-000000000000"
    print(f"[AUTH] Cloud mode fallback. Using DummyID: {fallback_id}")
    return {"id": fallback_id}
