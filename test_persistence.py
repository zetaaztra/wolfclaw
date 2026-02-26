
import os
import uuid
import json
from core import local_db
from core import bot_manager

def test_persistence():
    print("--- Local persistence sanity check ---")
    
    # 1. Setup clean env
    db_path = os.path.join(os.path.expanduser("~"), ".wolfclaw", "wolfclaw_local.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    local_db.init_db()
    
    # 2. Create User & Session
    user_id = local_db.create_user("test@example.com", "pass:salt")
    session_id = local_db.create_session(user_id)
    print(f"Created user {user_id} and session {session_id}")
    
    # 3. Create Bot via bot_manager (which uses _get_active_workspace_id)
    os.environ["WOLFCLAW_ENVIRONMENT"] = "desktop"
    bot_id = str(uuid.uuid4())
    bot_manager.save_bot(bot_id, "PersistenceBot", "gpt-4o", "Pirate prompt", user_id=user_id)
    print(f"Saved bot {bot_id} via bot_manager")
    
    # 4. Retrieve bots for that user
    bots = bot_manager.get_bots(user_id=user_id)
    print(f"Retrieved bots: {list(bots.keys())}")
    
    if bot_id in bots:
        print("SUCCESS: Bot found in user workspace")
    else:
        print("FAILURE: Bot NOT found in user workspace")
        # Check workspaces
        workspaces = local_db.get_workspaces_for_user(user_id)
        print(f"Workspaces for user: {workspaces}")
        for ws in workspaces:
            ws_bots = local_db.get_bots_for_workspace(ws['id'])
            print(f"Bots in workspace {ws['id']}: {list(ws_bots.keys())}")

if __name__ == "__main__":
    test_persistence()
