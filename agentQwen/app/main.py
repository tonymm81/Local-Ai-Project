from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from db import save_prompt, init_db
import os, httpx

app = FastAPI(title="AI Agent 3 (qwen controller)")

QWEN_URL = os.getenv("QWEN_URL", "http://ollama:11434")  # docker-compose ylikirjoittaa tämän

# --- TÄRKEÄ: rekisteröi startup-event ---
@app.on_event("startup")
async def startup_event():
    await init_db()

class GenReq(BaseModel):
    prompt: str
    model: str | None = None

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/generate")
async def generate(req: GenReq):
    if not req.prompt:
        raise HTTPException(status_code=400, detail="prompt required")

    try:
        async with httpx.AsyncClient(timeout=60.0) as c:
            payload = {
                "model": req.model or "qwen2.5:7b",
                "messages": [
                    {"role": "user", "content": req.prompt}
                ],
                "stream": False
            }

            r = await c.post(f"{QWEN_URL}/api/chat", json=payload)
            r.raise_for_status()

            data = r.json()
            text = data["message"]["content"]

            resp = {
                "request_id": "agent3",
                "model": payload["model"],
                "text": text,
                "tokens": len(text.split())
            }

    except Exception as e:
        print("GEN ERROR:", e)
        resp = {
            "request_id": "agent3-echo",
            "model": req.model or "dev",
            "text": req.prompt,
            "tokens": len(req.prompt.split())
        }

    try:
        await save_prompt(
            user_id="local",
            model=resp.get("model", "unknown"),
            prompt=req.prompt,
            resp_text=resp.get("text", "")
        )
    except Exception as e:
        print("DB save error:", e)

    return resp
