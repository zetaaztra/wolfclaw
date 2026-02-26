from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os

# Using the existing local database module to keep our changes modular
from core import local_db

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str

class ResetRequest(BaseModel):
    email: str
    recovery_key: str
    new_password: str

@router.post("/login")
async def login(req: LoginRequest):
    """Local SQLite Login"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    user = local_db.get_user(req.email)
    if user:
        try:
            # Check password hash using the salt:hash format
            import hashlib
            parts = user["password_hash"].split(':')
            if len(parts) == 2:
                hash_val, salt = parts[0], parts[1]
                test_hash = hashlib.sha256(salt.encode() + req.password.encode()).hexdigest()
                if test_hash == hash_val:
                    session_id = local_db.create_session(user["id"])
                    return {
                        "status": "success", 
                        "user_id": user["id"], 
                        "email": user["email"],
                        "session_id": session_id
                    }
            else:
                # Handle legacy plain-text or single-part hashes for migration safety
                if req.password == user["password_hash"]:
                    session_id = local_db.create_session(user["id"])
                    return {
                        "status": "success", 
                        "user_id": user["id"], 
                        "email": user["email"],
                        "session_id": session_id
                    }
        except Exception:
            pass
            
    raise HTTPException(status_code=401, detail="Invalid email or password.")

@router.post("/register")
async def register(req: RegisterRequest):
    """Local SQLite Registration"""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Route restricted to Desktop environment.")
        
    try:
        # Create a secure hash for the password
        import hashlib
        import secrets
        salt = secrets.token_hex(8)
        password_hash = hashlib.sha256(salt.encode() + req.password.encode()).hexdigest() + ':' + salt
        
        # Generate Master Recovery Key (only shown once)
        recovery_key = secrets.token_urlsafe(12)
        rec_salt = secrets.token_hex(8)
        recovery_key_hash = hashlib.sha256(rec_salt.encode() + recovery_key.encode()).hexdigest() + ':' + rec_salt
        
        user_id = local_db.create_user(req.email, password_hash, recovery_key_hash)
        return {
            "status": "success", 
            "user_id": user_id, 
            "email": req.email,
            "recovery_key": recovery_key
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reset")
async def reset_password(req: ResetRequest):
    """Offline Password Reset via Master Recovery Key"""
    user = local_db.get_user(req.email)
    if not user or not user["recovery_key_hash"]:
        raise HTTPException(status_code=400, detail="Invalid email or recovery key.")
        
    import hashlib
    parts = user["recovery_key_hash"].split(':')
    if len(parts) == 2:
        hash_val, rec_salt = parts[0], parts[1]
        test_hash = hashlib.sha256(rec_salt.encode() + req.recovery_key.encode()).hexdigest()
        
        if test_hash == hash_val:
            # Valid recovery key! Set new password.
            import secrets
            salt = secrets.token_hex(8)
            new_password_hash = hashlib.sha256(salt.encode() + req.new_password.encode()).hexdigest() + ':' + salt
            local_db.update_user_password(user["id"], new_password_hash)
            return {"status": "success", "message": "Password successfully reset."}
            
    raise HTTPException(status_code=400, detail="Invalid email or recovery key.")

class ChangePasswordRequest(BaseModel):
    user_id: str
    current_password: str
    new_password: str

@router.post("/change-password")
async def change_password(req: ChangePasswordRequest):
    """Change Password for logged-in user"""
    # SQLite has no get_user_by_id directly in the current local_db API, so we will fetch all or use a new method.
    # Actually, we can just do a direct query here since it's local SQLite
    conn = local_db._get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (req.user_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="User not found.")
        
    user = dict(row)
    import hashlib
    parts = user["password_hash"].split(':')
    if len(parts) == 2:
        hash_val, salt = parts[0], parts[1]
        test_hash = hashlib.sha256(salt.encode() + req.current_password.encode()).hexdigest()
        if test_hash != hash_val:
            raise HTTPException(status_code=401, detail="Incorrect current password.")
    else:
        if req.current_password != user["password_hash"]:
            raise HTTPException(status_code=401, detail="Incorrect current password.")
            
    # Hash new password
    import secrets
    new_salt = secrets.token_hex(8)
    new_password_hash = hashlib.sha256(new_salt.encode() + req.new_password.encode()).hexdigest() + ':' + new_salt
    local_db.update_user_password(user["id"], new_password_hash)
    
    return {"status": "success", "message": "Password successfully updated."}

@router.post("/logout")
async def logout(session_id: str):
    """Invalidate a session"""
    local_db.delete_session(session_id)
    return {"status": "success", "message": "Logged out."}
