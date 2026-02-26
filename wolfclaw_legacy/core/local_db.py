from __future__ import annotations
import sqlite3
import os
import json
import uuid
from typing import Dict, List, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.expanduser("~"), ".wolfclaw", "wolfclaw_local.db")

def _get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _get_connection()
    c = conn.cursor()
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        recovery_key_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS workspaces (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        ssh_config TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS bots (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        name TEXT NOT NULL,
        model TEXT NOT NULL,
        prompt TEXT NOT NULL,
        fallback_models TEXT DEFAULT '[]',
        telegram_token TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS vault (
        user_id TEXT PRIMARY KEY,
        openai_key TEXT,
        anthropic_key TEXT,
        nvidia_key TEXT,
        google_key TEXT,
        deepseek_key TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS favorites (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        bot_name TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS recovery_tokens (
        user_id TEXT PRIMARY KEY,
        token TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # --- SCHEMA MIGRATIONS ---
    # Vault table
    c.execute("PRAGMA table_info(vault)")
    vault_cols = [col['name'] for col in c.fetchall()]
    if 'deepseek_key' not in vault_cols:
        c.execute("ALTER TABLE vault ADD COLUMN deepseek_key TEXT")

    # Users table migration for recovery key
    c.execute("PRAGMA table_info(users)")
    users_cols = [col['name'] for col in c.fetchall()]
    if 'recovery_key_hash' not in users_cols:
        c.execute("ALTER TABLE users ADD COLUMN recovery_key_hash TEXT")
    
    # Bots table
    c.execute("PRAGMA table_info(bots)")
    bots_cols = [col['name'] for col in c.fetchall()]
    if 'fallback_models' not in bots_cols:
        c.execute("ALTER TABLE bots ADD COLUMN fallback_models TEXT DEFAULT '[]'")
    if 'telegram_token' not in bots_cols:
        c.execute("ALTER TABLE bots ADD COLUMN telegram_token TEXT")

    # Workspaces table
    c.execute("PRAGMA table_info(workspaces)")
    ws_cols = [col['name'] for col in c.fetchall()]
    if 'ssh_config' not in ws_cols:
        c.execute("ALTER TABLE workspaces ADD COLUMN ssh_config TEXT DEFAULT '{}'")

    # Documents table
    c.execute("PRAGMA table_info(documents)")
    if not c.fetchall():
        c.execute('''
        CREATE TABLE documents (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            content_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        )
        ''')

    # Chat history table
    c.execute("PRAGMA table_info(chat_history)")
    if not c.fetchall():
        c.execute('''
        CREATE TABLE chat_history (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            title TEXT DEFAULT 'New Chat',
            messages TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        )
        ''')

    # Knowledge base documents table
    c.execute("PRAGMA table_info(knowledge_docs)")
    if not c.fetchall():
        c.execute('''
        CREATE TABLE knowledge_docs (
            id TEXT PRIMARY KEY,
            bot_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            chunk_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(bot_id) REFERENCES bots(id) ON DELETE CASCADE
        )
        ''')

    # Knowledge base chunks table
    c.execute("PRAGMA table_info(knowledge_chunks)")
    if not c.fetchall():
        c.execute('''
        CREATE TABLE knowledge_chunks (
            id TEXT PRIMARY KEY,
            bot_id TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            doc_name TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            keywords TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(bot_id) REFERENCES bots(id) ON DELETE CASCADE
        )
        ''')

    # Usage logs table (Phase 17)
    c.execute("PRAGMA table_info(usage_logs)")
    if not c.fetchall():
        c.execute('''
        CREATE TABLE usage_logs (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            bot_id TEXT,
            model TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            estimated_cost REAL DEFAULT 0.0,
            response_time_ms INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

    # Scheduled tasks table (Phase 14)
    c.execute("PRAGMA table_info(scheduled_tasks)")
    if not c.fetchall():
        c.execute('''
        CREATE TABLE scheduled_tasks (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            name TEXT NOT NULL,
            prompt TEXT NOT NULL,
            schedule_type TEXT DEFAULT 'interval',
            schedule_value TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            last_run TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        )
        ''')

    # Task results table (Phase 14)
    c.execute("PRAGMA table_info(task_results)")
    if not c.fetchall():
        c.execute('''
        CREATE TABLE task_results (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(task_id) REFERENCES scheduled_tasks(id) ON DELETE CASCADE
        )
        ''')

    # Flows table (Phase 27 — Visual Workflow Builder)
    c.execute("PRAGMA table_info(flows)")
    if not c.fetchall():
        c.execute('''
        CREATE TABLE flows (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            flow_data TEXT NOT NULL DEFAULT '{}',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        )
        ''')

    conn.commit()
    conn.close()

# Users
def create_user(email: str, password_hash: str, recovery_key_hash: str = None) -> str:
    conn = _get_connection()
    c = conn.cursor()
    user_id = str(uuid.uuid4())
    try:
        c.execute(
            "INSERT INTO users (id, email, password_hash, recovery_key_hash) VALUES (?, ?, ?, ?)", 
            (user_id, email, password_hash, recovery_key_hash)
        )
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        raise ValueError("Email already exists")
    finally:
        conn.close()

def get_user_by_email(email: str) -> Optional[Dict]:
    conn = _get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user(email: str) -> Optional[Dict]:
    """Alias for get_user_by_email to match API expectations."""
    return get_user_by_email(email)

def update_user_password(user_id: str, new_password_hash: str):
    conn = _get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id: str):
    conn = _get_connection()
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# Workspaces
def create_workspace(user_id: str, name: str) -> str:
    conn = _get_connection()
    c = conn.cursor()
    ws_id = str(uuid.uuid4())
    c.execute("INSERT INTO workspaces (id, user_id, name) VALUES (?, ?, ?)", (ws_id, user_id, name))
    conn.commit()
    conn.close()
    return ws_id

def get_workspaces_for_user(user_id: str) -> List[Dict]:
    conn = _get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM workspaces WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    
    res = []
    for r in rows:
        d = dict(r)
        d['ssh_config'] = json.loads(d['ssh_config']) if d['ssh_config'] else {}
        res.append(d)
    return res

def update_workspace_ssh(ws_id: str, ssh_data_list: list):
    conn = _get_connection()
    c = conn.cursor()
    c.execute("UPDATE workspaces SET ssh_config = ? WHERE id = ?", (json.dumps(ssh_data_list), ws_id))
    conn.commit()
    conn.close()
    
def get_workspace_ssh(ws_id: str) -> list:
    conn = _get_connection()
    c = conn.cursor()
    c.execute("SELECT ssh_config FROM workspaces WHERE id = ?", (ws_id,))
    row = c.fetchone()
    conn.close()
    if row and row['ssh_config']:
        data = json.loads(row['ssh_config'])
        # Migrate legacy single dict to list
        if isinstance(data, dict):
            if not data: return []
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            return [data]
        return data
    return []

# Bots
def create_bot(ws_id: str, name: str, model: str, prompt: str, fallback_models: List[str] = None) -> str:
    if fallback_models is None:
        fallback_models = []
    conn = _get_connection()
    c = conn.cursor()
    bot_id = str(uuid.uuid4())
    c.execute(
        "INSERT INTO bots (id, workspace_id, name, model, prompt, fallback_models) VALUES (?, ?, ?, ?, ?, ?)",
        (bot_id, ws_id, name, model, prompt, json.dumps(fallback_models))
    )
    conn.commit()
    conn.close()
    return bot_id

def get_bots_for_workspace(ws_id: str) -> Dict[str, Dict]:
    conn = _get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE workspace_id = ?", (ws_id,))
    rows = c.fetchall()
    conn.close()
    
    bots = {}
    for r in rows:
        b = dict(r)
        bots[b['id']] = {
            "id": b['id'],
            "name": b['name'],
            "model": b['model'],
            "prompt": b['prompt'],
            "fallback_models": json.loads(b['fallback_models']) if b['fallback_models'] else [],
            "telegram_token": b['telegram_token']
        }
    return bots

def update_bot_prompt(bot_id: str, new_prompt: str):
    conn = _get_connection()
    c = conn.cursor()
    c.execute("UPDATE bots SET prompt = ? WHERE id = ?", (new_prompt, bot_id))
    conn.commit()
    conn.close()
    
def update_bot_telegram(bot_id: str, token: str):
    conn = _get_connection()
    c = conn.cursor()
    c.execute("UPDATE bots SET telegram_token = ? WHERE id = ?", (token, bot_id))
    conn.commit()
    conn.close()
    
def delete_bot(bot_id: str):
    conn = _get_connection()
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON")
    
    # 1. Delete associated data from tables that might not have CASCADE or FKs
    c.execute("DELETE FROM chat_history WHERE bot_id = ?", (bot_id,))
    
    # Delete task results first as they reference scheduled_tasks
    c.execute("DELETE FROM task_results WHERE task_id IN (SELECT id FROM scheduled_tasks WHERE bot_id = ?)", (bot_id,))
    c.execute("DELETE FROM scheduled_tasks WHERE bot_id = ?", (bot_id,))
    
    c.execute("DELETE FROM usage_logs WHERE bot_id = ?", (bot_id,))
    
    # 2. Delete the bot itself (will cascade to knowledge_docs and knowledge_chunks)
    c.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
    
    conn.commit()
    conn.close()

# Vault
def set_key_local(user_id: str, col_name: str, key: str):
    conn = _get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM vault WHERE user_id = ?", (user_id,))
    if c.fetchone():
        c.execute(f"UPDATE vault SET {col_name} = ? WHERE user_id = ?", (key, user_id))
    else:
        c.execute(f"INSERT INTO vault (user_id, {col_name}) VALUES (?, ?)", (user_id, key))
    conn.commit()
    conn.close()

def get_key_local(user_id: str, col_name: str) -> str:
    conn = _get_connection()
    c = conn.cursor()
    c.execute(f"SELECT {col_name} FROM vault WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row and row[col_name]:
        return row[col_name]
    return ""

def store_recovery_token(user_id: str, token: str):
    conn = _get_connection()
    c = conn.cursor()
    expires_at = datetime.now().isoformat() # For simplicity, 1 hour isn't enforced yet
    c.execute("INSERT OR REPLACE INTO recovery_tokens (user_id, token, expires_at) VALUES (?, ?, ?)", (user_id, token, expires_at))
    conn.commit()
    conn.close()

init_db()

# -------------------------------------------------------------------------------------
# Documents (File Upload for Context)
# -------------------------------------------------------------------------------------

def save_document(ws_id: str, filename: str, content_text: str) -> str:
    """Save parsed document text to the database."""
    conn = _get_connection()
    c = conn.cursor()
    doc_id = str(uuid.uuid4())
    c.execute('''
        INSERT INTO documents (id, workspace_id, filename, content_text)
        VALUES (?, ?, ?, ?)
    ''', (doc_id, ws_id, filename, content_text))
    conn.commit()
    conn.close()
    return doc_id

def get_documents_for_workspace(ws_id: str) -> List[Dict]:
    """Retrieve all documents uploaded to a workspace."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('SELECT id, filename, created_at FROM documents WHERE workspace_id = ? ORDER BY created_at DESC', (ws_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_document_content(doc_id: str) -> Optional[str]:
    """Retrieve the full parsed text of a document."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('SELECT content_text FROM documents WHERE id = ?', (doc_id,))
    row = c.fetchone()
    conn.close()
    return row['content_text'] if row else None

def delete_document(doc_id: str):
    """Delete a document."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
    conn.commit()
    conn.close()

# -------------------------------------------------------------------------------------
# Chat History (Persistent Conversations)
# -------------------------------------------------------------------------------------

def save_chat_history(ws_id: str, bot_id: str, title: str, messages: str, chat_id: Optional[str] = None) -> str:
    """Create or update a chat history thread."""
    conn = _get_connection()
    c = conn.cursor()
    
    if chat_id:
        # Update existing
        c.execute('''
            UPDATE chat_history 
            SET title = ?, messages = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND workspace_id = ?
        ''', (title, messages, chat_id, ws_id))
    else:
        # Create new
        chat_id = str(uuid.uuid4())
        c.execute('''
            INSERT INTO chat_history (id, workspace_id, bot_id, title, messages)
            VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, ws_id, bot_id, title, messages))
        
    conn.commit()
    conn.close()
    return chat_id

def get_chat_histories(ws_id: str) -> List[Dict]:
    """Get all chat histories for a workspace."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, bot_id, title, created_at, updated_at 
        FROM chat_history 
        WHERE workspace_id = ? 
        ORDER BY updated_at DESC
    ''', (ws_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_chat_history(chat_id: str) -> Optional[Dict]:
    """Get full details of a specific chat history."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM chat_history WHERE id = ?', (chat_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_chat_history(chat_id: str):
    """Delete a chat history."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM chat_history WHERE id = ?', (chat_id,))
    conn.commit()
    conn.close()

# ─────────── Knowledge Base (Phase 13) ───────────

def save_knowledge_doc(bot_id: str, filename: str, chunk_count: int) -> str:
    """Save a knowledge base document record."""
    conn = _get_connection()
    c = conn.cursor()
    doc_id = str(uuid.uuid4())
    c.execute('''
        INSERT INTO knowledge_docs (id, bot_id, filename, chunk_count)
        VALUES (?, ?, ?, ?)
    ''', (doc_id, bot_id, filename, chunk_count))
    conn.commit()
    conn.close()
    return doc_id

def save_knowledge_chunks(chunks: list):
    """Bulk insert knowledge chunks. Each chunk is a dict with id, bot_id, doc_id, doc_name, chunk_index, content, keywords."""
    conn = _get_connection()
    c = conn.cursor()
    for ch in chunks:
        c.execute('''
            INSERT INTO knowledge_chunks (id, bot_id, doc_id, doc_name, chunk_index, content, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (ch['id'], ch['bot_id'], ch['doc_id'], ch['doc_name'], ch['chunk_index'], ch['content'], ch['keywords']))
    conn.commit()
    conn.close()

def get_knowledge_docs(bot_id: str) -> List[Dict]:
    """List all knowledge docs for a bot."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM knowledge_docs WHERE bot_id = ? ORDER BY created_at DESC', (bot_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_knowledge_chunks_for_bot(bot_id: str) -> List[Dict]:
    """Get ALL chunks for a bot (used for search)."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM knowledge_chunks WHERE bot_id = ? ORDER BY doc_name, chunk_index', (bot_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_knowledge_doc(doc_id: str):
    """Delete a knowledge doc and all its chunks."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM knowledge_chunks WHERE doc_id = ?', (doc_id,))
    c.execute('DELETE FROM knowledge_docs WHERE id = ?', (doc_id,))
    conn.commit()
    conn.close()

# ─────────── Usage Analytics (Phase 17) ───────────

def log_usage(ws_id: str, bot_id: str, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, estimated_cost: float, response_time_ms: int):
    """Log a single LLM API call."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO usage_logs (id, workspace_id, bot_id, model, prompt_tokens, completion_tokens, total_tokens, estimated_cost, response_time_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (str(uuid.uuid4()), ws_id, bot_id, model, prompt_tokens, completion_tokens, total_tokens, estimated_cost, response_time_ms))
    conn.commit()
    conn.close()

def get_usage_summary(ws_id: str) -> Dict:
    """Get aggregate usage stats."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT 
            COUNT(*) as total_calls,
            COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
            COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
            COALESCE(SUM(total_tokens), 0) as total_tokens,
            COALESCE(SUM(estimated_cost), 0.0) as total_cost,
            COALESCE(AVG(response_time_ms), 0) as avg_response_ms
        FROM usage_logs WHERE workspace_id = ?
    ''', (ws_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else {}

def get_usage_by_model(ws_id: str) -> List[Dict]:
    """Get usage breakdown by model."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT model, COUNT(*) as calls, SUM(total_tokens) as tokens, SUM(estimated_cost) as cost
        FROM usage_logs WHERE workspace_id = ?
        GROUP BY model ORDER BY tokens DESC
    ''', (ws_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_usage_by_bot(ws_id: str) -> List[Dict]:
    """Get usage breakdown by bot."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT bot_id, COUNT(*) as calls, SUM(total_tokens) as tokens, SUM(estimated_cost) as cost
        FROM usage_logs WHERE workspace_id = ?
        GROUP BY bot_id ORDER BY tokens DESC
    ''', (ws_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_usage_daily(ws_id: str, days: int = 30) -> List[Dict]:
    """Get daily usage for charting."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT DATE(created_at) as day, COUNT(*) as calls, SUM(total_tokens) as tokens, SUM(estimated_cost) as cost
        FROM usage_logs WHERE workspace_id = ?
        GROUP BY DATE(created_at) ORDER BY day DESC LIMIT ?
    ''', (ws_id, days))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ─────────── Scheduled Tasks (Phase 14) ───────────

def create_scheduled_task(ws_id: str, bot_id: str, name: str, prompt: str, schedule_type: str, schedule_value: str) -> str:
    """Create a new scheduled task."""
    conn = _get_connection()
    c = conn.cursor()
    task_id = str(uuid.uuid4())
    c.execute('''
        INSERT INTO scheduled_tasks (id, workspace_id, bot_id, name, prompt, schedule_type, schedule_value)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (task_id, ws_id, bot_id, name, prompt, schedule_type, schedule_value))
    conn.commit()
    conn.close()
    return task_id

def get_scheduled_tasks(ws_id: str) -> List[Dict]:
    """Get all scheduled tasks for a workspace."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM scheduled_tasks WHERE workspace_id = ? ORDER BY created_at DESC', (ws_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_scheduled_task(task_id: str) -> Optional[Dict]:
    """Get a specific scheduled task."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM scheduled_tasks WHERE id = ?', (task_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_scheduled_task(task_id: str, **kwargs):
    """Update a scheduled task's fields."""
    conn = _get_connection()
    c = conn.cursor()
    for key, val in kwargs.items():
        c.execute(f'UPDATE scheduled_tasks SET {key} = ? WHERE id = ?', (val, task_id))
    conn.commit()
    conn.close()

def delete_scheduled_task(task_id: str):
    """Delete a scheduled task and its results."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM task_results WHERE task_id = ?', (task_id,))
    c.execute('DELETE FROM scheduled_tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

def save_task_result(task_id: str, result: str) -> str:
    """Save a task execution result."""
    conn = _get_connection()
    c = conn.cursor()
    result_id = str(uuid.uuid4())
    c.execute('INSERT INTO task_results (id, task_id, result) VALUES (?, ?, ?)', (result_id, task_id, result))
    c.execute('UPDATE scheduled_tasks SET last_run = CURRENT_TIMESTAMP WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return result_id

def get_task_results(task_id: str, limit: int = 20) -> List[Dict]:
    """Get execution results for a task."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM task_results WHERE task_id = ? ORDER BY created_at DESC LIMIT ?', (task_id, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# -------------------------------------------------------------------------------------
# Flows (Phase 27 — Visual Workflow Builder)
# -------------------------------------------------------------------------------------

def save_flow(ws_id: str, name: str, description: str, flow_data: str, flow_id: Optional[str] = None) -> str:
    """Create or update a flow."""
    conn = _get_connection()
    c = conn.cursor()
    if flow_id:
        c.execute('UPDATE flows SET name = ?, description = ?, flow_data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                  (name, description, flow_data, flow_id))
    else:
        flow_id = str(uuid.uuid4())
        c.execute('INSERT INTO flows (id, workspace_id, name, description, flow_data) VALUES (?, ?, ?, ?, ?)',
                  (flow_id, ws_id, name, description, flow_data))
    conn.commit()
    conn.close()
    return flow_id

def get_flows_for_workspace(ws_id: str) -> List[Dict]:
    """List all flows for a workspace."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('SELECT id, workspace_id, name, description, is_active, created_at, updated_at FROM flows WHERE workspace_id = ? ORDER BY updated_at DESC', (ws_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_flow(flow_id: str) -> Optional[Dict]:
    """Get a single flow with its full data."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM flows WHERE id = ?', (flow_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_flow_status(flow_id: str, is_active: int):
    """Toggle a flow's active status."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('UPDATE flows SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (is_active, flow_id))
    conn.commit()
    conn.close()

def delete_flow(flow_id: str):
    """Delete a flow."""
    conn = _get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM flows WHERE id = ?', (flow_id,))
    conn.commit()
    conn.close()

init_db()
