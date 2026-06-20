from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from db import save_prompt
import httpx
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

app = FastAPI(title="Ollama Dev Agent")

class GenReq(BaseModel):
    prompt: str
    model: str | None = "phi_2_gguf:latest"

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/generate")
async def generate(req: GenReq):
    if not req.prompt:
        raise HTTPException(status_code=400, detail="prompt required")

    payload = {
        "model": req.model,
        "prompt": req.prompt,
        "stream": False
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            raw_body = None
            try:
                raw_body = r.text
            except Exception:
                raw_body = "<could not read response body>"
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError:
                raise HTTPException(status_code=500, detail=f"Ollama HTTP {r.status_code}: {raw_body}")
            data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {repr(e)}")

    text = data.get("response") or data.get("text") or ""

    # Save to SQLite
    try:
        await save_prompt(
            user_id="local",
            model=req.model,
            prompt=req.prompt,
            resp_text=text
        )
    except Exception as e:
        print("DB save error:", e)

    return {
        "request_id": data.get("id", "ollama-dev"),
        "model": req.model,
        "text": text,
        "tokens": len(text.split())
    }
