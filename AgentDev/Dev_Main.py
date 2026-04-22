from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from db import save_prompt

app = FastAPI(title="Dev Agent (echo)")

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

    resp = {
        "request_id": "dev-echo-1",
        "model": req.model or "dev",
        "text": req.prompt,
        "tokens": len(req.prompt.split())
    }

    # Save to SQLite
    try:
        await save_prompt(
            user_id="local",
            model=resp["model"],
            prompt=req.prompt,
            resp_text=resp["text"]
        )
    except Exception as e:
        print("DB save error:", e)

    return resp