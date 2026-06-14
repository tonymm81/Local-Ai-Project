import os
import aiosqlite

DB_PATH = os.getenv("SQLITE_PATH", "/data/agent.db")

async def save_prompt(user_id, model, prompt, resp_text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO prompts (user_id, model, prompt_text, response_text) VALUES (?,?,?,?)",
            (user_id, model, prompt, resp_text)
        )
        await db.commit()