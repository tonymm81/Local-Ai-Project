import os
import httpx
import mysql.connector
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title=os.getenv("APP_TITLE", "Local AI Agent"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "mariadb"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "database": os.getenv("DB_NAME"),
}
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
API_KEY = os.getenv("API_KEY", "changeme")

class GenRequest(BaseModel):
    prompt: str
    model: str = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")
    user_id: str | None = None

@app.post("/api/generate")
async def generate(req: GenRequest, authorization: str | None = Header(None)):
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(f"{OLLAMA_URL}/api/generate", json={"prompt": req.prompt, "model": req.model})
        r.raise_for_status()
        resp = r.json()

    cnx = mysql.connector.connect(**DB_CONFIG)
    cur = cnx.cursor()
    cur.execute(
        "INSERT INTO prompts (user_id, model, prompt_text, response_text) VALUES (%s,%s,%s,%s)",
        (req.user_id, req.model, req.prompt, str(resp)),
    )
    cnx.commit()
    cur.close()
    cnx.close()

    return {"result": resp}