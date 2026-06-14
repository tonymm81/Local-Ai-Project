# /app/db.py
import os
import aiosqlite

DB_PATH = os.getenv("SQLITE_PATH", os.getenv("DATABASE_PATH", "/data/agent.db"))

async def init_db():
    # Luo tarvittavat taulut jos puuttuvat
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            model TEXT,
            prompt_text TEXT,
            response_text TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.commit()

async def save_prompt(user_id, model, prompt, resp_text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO prompts (user_id, model, prompt_text, response_text) VALUES (?,?,?,?)",
            (user_id, model, prompt, resp_text)
        )
        await db.commit()
