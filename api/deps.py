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
            print("[AUTH] FAILED: No Bearer token provided.")
            raise HTTPException(status_code=401, detail="Authentication required. Please login.")
            
        token_prefix = auth.credentials[:8]
        print(f"[AUTH] Resolving session for token: {token_prefix}...")
        session = local_db.get_session(auth.credentials)
        
        if not session:
            print(f"[AUTH] FAILED: Invalid or expired session token: {token_prefix}...")
            raise HTTPException(status_code=401, detail="Invalid or expired session. Please login again.")
        
        user_id = session["user_id"]
        print(f"[AUTH] SUCCESS: Resolved UserID: {user_id}")
        return {"id": user_id}
        
    # Restricted mode for non-desktop environments
    raise HTTPException(status_code=403, detail="API access limited to local desktop instances.")
