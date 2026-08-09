# db.py
# MariaDB handler for Pixatrail agent
# Provides async-compatible functions (uses asyncio.to_thread to run blocking mysql.connector calls)
# Functions:
#   init_db
#   save_prompt
#   get_conversations
#   get_messages_by_title
#   get_last_rows_by_title
#   get_latest_conversation_by_title
#   delete_conversation_by_title
#
# Expects environment variables:
#   DB_HOST, DB_USER, DB_PASS, DB_NAME

import os
import asyncio
from typing import List, Dict, Optional
import mysql.connector
from mysql.connector import Error

DB_HOST = os.getenv("DB_HOST", "mariadb")
DB_USER = os.getenv("DB_USER", "agent1")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "agent1_db")


def _get_conn():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        autocommit=False,
    )


def _ensure_indexes(cur):
    # MySQL doesn't support IF NOT EXISTS for CREATE INDEX in older versions,
    # so attempt to create and ignore errors if index exists.
    try:
        cur.execute("CREATE INDEX idx_prompts_conversation_title ON prompts(conversation_title)")
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX idx_prompts_created_at ON prompts(created_at)")
    except Exception:
        pass


async def init_db() -> None:
    """
    Create prompts table if missing and ensure indexes.
    Call once at agent startup.
    """
    def _init():
        cnx = None
        try:
            cnx = _get_conn()
            cur = cnx.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS prompts (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  model VARCHAR(255),
                  prompt_text TEXT,
                  response_text LONGTEXT,
                  conversation_id VARCHAR(255),
                  conversation_title VARCHAR(255),
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
                """
            )
            # create indexes if not present (best-effort)
            _ensure_indexes(cur)
            cnx.commit()
            cur.close()
        finally:
            if cnx:
                try:
                    cnx.close()
                except Exception:
                    pass

    await asyncio.to_thread(_init)


async def save_prompt(model: str, prompt: str, resp_text: Optional[str] = None,
                      conversation_title: Optional[str] = None, conversation_id: Optional[str] = None) -> str:
    """
    Save a prompt+response pair to the DB.
    conversation_title is REQUIRED.
    Returns the conversation_id used for the insert (if provided or generated).
    """
    if not conversation_title:
        raise ValueError("conversation_title is required")

    # If caller didn't provide conversation_id, keep it NULL (compat with schema).
    def _save():
        cnx = None
        try:
            cnx = _get_conn()
            cur = cnx.cursor()
            cur.execute(
                "INSERT INTO prompts (model, prompt_text, response_text, conversation_id, conversation_title, created_at) "
                "VALUES (%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)",
                (model, prompt, resp_text, conversation_id, conversation_title),
            )
            cnx.commit()
            last_id = cur.lastrowid
            cur.close()
            return conversation_id if conversation_id else str(last_id)
        finally:
            if cnx:
                try:
                    cnx.close()
                except Exception:
                    pass

    return await asyncio.to_thread(_save)


async def get_conversations(limit: int = 100, offset: int = 0) -> List[Dict]:
    """
    Return a list of conversations grouped by conversation_title.
    Each item: { conversation_title, last_updated, message_count }.
    Ordered by last_updated descending.
    """
    def _query():
        cnx = None
        rows = []
        try:
            cnx = _get_conn()
            cur = cnx.cursor()
            cur.execute(
                """
                SELECT conversation_title, MAX(created_at) as last_updated, COUNT(*) as message_count
                FROM prompts
                GROUP BY conversation_title
                ORDER BY last_updated DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            for r in cur.fetchall():
                rows.append({
                    "conversation_title": r[0],
                    "last_updated": r[1],
                    "message_count": r[2],
                })
            cur.close()
            return rows
        finally:
            if cnx:
                try:
                    cnx.close()
                except Exception:
                    pass

    return await asyncio.to_thread(_query)


async def get_messages_by_title(conversation_title: str, limit: int = 200, offset: int = 0) -> List[Dict]:
    """
    Return messages for a given conversation_title in chronological order (oldest -> newest).
    Each row contains id, model, prompt_text, response_text, created_at.
    """
    if not conversation_title:
        raise ValueError("conversation_title is required")

    def _query():
        cnx = None
        rows = []
        try:
            cnx = _get_conn()
            cur = cnx.cursor()
            cur.execute(
                """
                SELECT id, model, prompt_text, response_text, created_at
                FROM prompts
                WHERE conversation_title = %s
                ORDER BY created_at ASC
                LIMIT %s OFFSET %s
                """,
                (conversation_title, limit, offset),
            )
            for r in cur.fetchall():
                rows.append({
                    "id": r[0],
                    "model": r[1],
                    "prompt_text": r[2],
                    "response_text": r[3],
                    "created_at": r[4],
                })
            cur.close()
            return rows
        finally:
            if cnx:
                try:
                    cnx.close()
                except Exception:
                    pass

    return await asyncio.to_thread(_query)


async def get_last_rows_by_title(conversation_title: str, limit: int = 6) -> List[Dict]:
    """
    Fetch the last 'limit' prompt/response rows for a conversation_title and return them
    in chronological order (oldest -> newest).
    """
    if not conversation_title:
        raise ValueError("conversation_title is required")

    def _query():
        cnx = None
        rows = []
        try:
            cnx = _get_conn()
            cur = cnx.cursor()
            cur.execute(
                """
                SELECT id, model, prompt_text, response_text, created_at
                FROM prompts
                WHERE conversation_title = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (conversation_title, limit),
            )
            for r in cur.fetchall():
                rows.append({
                    "id": r[0],
                    "model": r[1],
                    "prompt_text": r[2],
                    "response_text": r[3],
                    "created_at": r[4],
                })
            cur.close()
            # reverse to chronological order
            return list(reversed(rows))
        finally:
            if cnx:
                try:
                    cnx.close()
                except Exception:
                    pass

    return await asyncio.to_thread(_query)


async def get_latest_conversation_by_title() -> Optional[Dict]:
    """
    Return the most recently updated conversation by title (conversation_title, last_updated),
    or None if there are no conversations.
    """
    def _query():
        cnx = None
        try:
            cnx = _get_conn()
            cur = cnx.cursor()
            cur.execute(
                """
                SELECT conversation_title, MAX(created_at) as last_updated
                FROM prompts
                GROUP BY conversation_title
                ORDER BY last_updated DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            cur.close()
            if not row:
                return None
            return {"conversation_title": row[0], "last_updated": row[1]}
        finally:
            if cnx:
                try:
                    cnx.close()
                except Exception:
                    pass

    return await asyncio.to_thread(_query)


async def delete_conversation_by_title(conversation_title: str) -> int:
    """
    Delete all rows that match the given conversation_title.
    Returns the number of deleted rows.
    """
    if not conversation_title:
        raise ValueError("conversation_title is required")

    def _delete():
        cnx = None
        try:
            cnx = _get_conn()
            cur = cnx.cursor()
            cur.execute("SELECT COUNT(*) FROM prompts WHERE conversation_title = %s", (conversation_title,))
            cnt_row = cur.fetchone()
            count_before = cnt_row[0] if cnt_row else 0
            cur.execute("DELETE FROM prompts WHERE conversation_title = %s", (conversation_title,))
            cnx.commit()
            cur.close()
            return count_before
        finally:
            if cnx:
                try:
                    cnx.close()
                except Exception:
                    pass

    return await asyncio.to_thread(_delete)
