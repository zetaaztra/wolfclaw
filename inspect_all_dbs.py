import sqlite3
import os

def inspect_db(db_path):
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return

    print(f"\n--- INSPECTING {db_path} ---")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in c.fetchall()]
        print(f"Tables: {tables}")

        if 'users' in tables:
            print("--- USERS ---")
            c.execute("SELECT id, email FROM users")
            for row in c.fetchall():
                print(dict(row))
        
        if 'vault' in tables:
            print("--- VAULT ---")
            c.execute("SELECT * FROM vault")
            for row in c.fetchall():
                print(dict(row))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_db("local_db.sqlite3")
    inspect_db("local_wolfclaw.db")
    inspect_db("wolfclaw_local.db")
    inspect_db("wolfclaw.db")
