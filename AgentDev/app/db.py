# db.py
# version: 109
# SQLite DB handler for dev agent
# - Uses conversation_title as the primary lookup key for conversation operations
# - Keeps conversation_id column for compatibility but queries operate by conversation_title
# - Functions: init_db, save_prompt, get_conversations, get_messages_by_title,
#   get_last_rows_by_title, get_latest_conversation_by_title, delete_conversation_by_title
# - WAL mode enabled (suitable for local Docker on Linux)

import os
import aiosqlite
import uuid
from typing import List, Dict, Optional

DB_PATH = os.getenv("SQLITE_PATH", "/data/agent.db")

async def _set_wal(db: aiosqlite.Connection) -> None:
    """
    Enable WAL mode on the connection.
    WAL improves concurrency and read performance on local filesystems.
    """
    try:
        await db.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        # If setting WAL fails, continue without raising to avoid breaking runtime.
        pass

async def init_db() -> None:
    """
    Initialize the database and create the prompts table if missing.
    Call this once at agent startup.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await _set_wal(db)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT,
            prompt_text TEXT,
            response_text TEXT,
            conversation_id TEXT,
            conversation_title TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_prompts_conversation_title ON prompts(conversation_title);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);")
        await db.commit()

async def save_prompt(model: str, prompt: str, resp_text: Optional[str] = None,
                      conversation_title: str = None, conversation_id: Optional[str] = None) -> str:
    """
    Save a prompt+response pair to the DB.
    conversation_title is REQUIRED and is used as the primary key for later lookups.
    conversation_id is optional and kept for compatibility; if not provided, a UUID is generated but NOT used for lookups.
    Returns the conversation_id used for the insert (may be generated).
    """
    if not conversation_title:
        raise ValueError("conversation_title is required")

    if conversation_id is None:
        conversation_id = str(uuid.uuid4())

    async with aiosqlite.connect(DB_PATH) as db:
        await _set_wal(db)
        await db.execute(
            "INSERT INTO prompts (model, prompt_text, response_text, conversation_id, conversation_title, created_at) VALUES (?,?,?,?,?,datetime('now'))",
            (model, prompt, resp_text, conversation_id, conversation_title)
        )
        await db.commit()
    return conversation_id

async def get_conversations(limit: int = 100, offset: int = 0) -> List[Dict]:
    """
    Return a list of conversations grouped by conversation_title.
    Each item: { conversation_title, last_updated, message_count }.
    Ordered by last_updated descending (most recent first).
    """
    query = """
    SELECT conversation_title, MAX(created_at) as last_updated, COUNT(*) as message_count
    FROM prompts
    GROUP BY conversation_title
    ORDER BY last_updated DESC
    LIMIT ? OFFSET ?
    """
    rows: List[Dict] = []
    async with aiosqlite.connect(DB_PATH) as db:
        await _set_wal(db)
        async with db.execute(query, (limit, offset)) as cur:
            async for r in cur:
                rows.append({
                    "conversation_title": r[0],
                    "last_updated": r[1],
                    "message_count": r[2]
                })
    return rows

async def get_messages_by_title(conversation_title: str, limit: int = 200, offset: int = 0) -> List[Dict]:
    """
    Return messages for a given conversation_title in chronological order (oldest -> newest).
    Each row contains the stored prompt_text and response_text pair.
    """
    if not conversation_title:
        raise ValueError("conversation_title is required")

    query = """
    SELECT id, model, prompt_text, response_text, created_at
    FROM prompts
    WHERE conversation_title = ?
    ORDER BY created_at ASC
    LIMIT ? OFFSET ?
    """
    rows: List[Dict] = []
    async with aiosqlite.connect(DB_PATH) as db:
        await _set_wal(db)
        async with db.execute(query, (conversation_title, limit, offset)) as cur:
            async for r in cur:
                rows.append({
                    "id": r[0],
                    "model": r[1],
                    "prompt_text": r[2],
                    "response_text": r[3],
                    "created_at": r[4]
                })
    return rows

async def get_last_rows_by_title(conversation_title: str, limit: int = 6) -> List[Dict]:
    """
    Fetch the last 'limit' prompt/response rows for a conversation_title and return them
    in chronological order (oldest -> newest). Useful for building agent context.
    """
    if not conversation_title:
        raise ValueError("conversation_title is required")

    query = """
    SELECT id, model, prompt_text, response_text, created_at
    FROM prompts
    WHERE conversation_title = ?
    ORDER BY created_at DESC
    LIMIT ?
    """
    rows: List[Dict] = []
    async with aiosqlite.connect(DB_PATH) as db:
        await _set_wal(db)
        async with db.execute(query, (conversation_title, limit)) as cur:
            async for r in cur:
                rows.append({
                    "id": r[0],
                    "model": r[1],
                    "prompt_text": r[2],
                    "response_text": r[3],
                    "created_at": r[4]
                })
    # Reverse to chronological order
    return list(reversed(rows))

async def get_latest_conversation_by_title() -> Optional[Dict]:
    """
    Return the most recently updated conversation by title (conversation_title, last_updated),
    or None if there are no conversations.
    """
    query = """
    SELECT conversation_title, MAX(created_at) as last_updated
    FROM prompts
    GROUP BY conversation_title
    ORDER BY last_updated DESC
    LIMIT 1
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await _set_wal(db)
        async with db.execute(query) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {
                "conversation_title": row[0],
                "last_updated": row[1]
            }

async def delete_conversation_by_title(conversation_title: str) -> int:
    """
    Delete all rows that match the given conversation_title.
    Returns the number of deleted rows.
    Deletion is by title as requested (no id-based delete function).
    """
    if not conversation_title:
        raise ValueError("conversation_title is required")

    async with aiosqlite.connect(DB_PATH) as db:
        await _set_wal(db)
        async with db.execute("SELECT COUNT(*) FROM prompts WHERE conversation_title = ?", (conversation_title,)) as cur:
            cnt_row = await cur.fetchone()
            count_before = cnt_row[0] if cnt_row else 0
        await db.execute("DELETE FROM prompts WHERE conversation_title = ?", (conversation_title,))
        await db.commit()
    return count_before
