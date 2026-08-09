# main.py
import os
import httpx
import traceback
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from db import (
    init_db,
    save_prompt,
    get_conversations,
    get_messages_by_title,
    get_last_rows_by_title,
    delete_conversation_by_title,
    get_latest_conversation_by_title,
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
API_KEY = os.getenv("API_KEY", "changeme")

app = FastAPI(title=os.getenv("APP_TITLE", "Local AI Agent"))

class GenRequest(BaseModel):
    prompt: str
    conversation_title: str
    model: Optional[str] = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")
    user_id: Optional[str] = None

# Ensure DB schema exists at startup
@app.on_event("startup")
async def startup_event():
    try:
        await init_db()
    except Exception:
        print("DB init error:")
        traceback.print_exc()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/generate")
async def generate(req: GenRequest, authorization: str | None = Header(None)):
    #if authorization != f"Bearer {API_KEY}":
        #raise HTTPException(status_code=401, detail="Unauthorized")

    if not req.prompt:
        raise HTTPException(status_code=400, detail="prompt required")
    if not req.conversation_title:
        raise HTTPException(status_code=400, detail="conversation_title required")

    payload = {
        "model": req.model,
        "prompt": req.prompt,
        "stream": True
    }

    full_text = ""
    upstream_id = None

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/generate", json=payload) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    body_text = body.decode("utf-8", errors="replace") if body else "<no body>"
                    raise HTTPException(status_code=500, detail=f"Ollama HTTP {resp.status_code}: {body_text}")

                line_buf = ""
                async for chunk in resp.aiter_text():
                    if not chunk:
                        continue
                    line_buf += chunk
                    lines = line_buf.split("\n")
                    if not line_buf.endswith("\n"):
                        line_buf = lines.pop()
                    else:
                        line_buf = ""
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            import json as _json
                            parsed = _json.loads(line)
                            candidate = None
                            if isinstance(parsed, dict):
                                candidate = parsed.get("response") or parsed.get("text")
                                if not candidate and isinstance(parsed.get("message"), dict):
                                    candidate = parsed["message"].get("content")
                                if parsed.get("id"):
                                    upstream_id = parsed.get("id")
                            if candidate:
                                full_text += candidate
                            else:
                                full_text += " "
                        except Exception:
                            full_text += line + " "

                # leftover partial line
                if line_buf:
                    tail = line_buf.strip()
                    if tail:
                        try:
                            import json as _json
                            parsed = _json.loads(tail)
                            candidate = parsed.get("response") or parsed.get("text") if isinstance(parsed, dict) else None
                            if candidate:
                                full_text += candidate
                            else:
                                full_text += " "
                        except Exception:
                            full_text += tail

                # try final body if present
                try:
                    raw = await resp.aread()
                    if raw:
                        import json as _json
                        parsed = _json.loads(raw.decode("utf-8", errors="replace"))
                        if isinstance(parsed, dict):
                            candidate = parsed.get("response") or parsed.get("text") or (parsed.get("message") or {}).get("content")
                            if candidate:
                                full_text = candidate
                            if parsed.get("id"):
                                upstream_id = parsed.get("id")
                except Exception:
                    pass

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Ollama request error: {repr(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {repr(e)}")

    # Normalize whitespace and compute tokens
    full_text = " ".join(full_text.split())
    tokens = len(full_text.split()) if full_text else 0

    # Save to DB using save_prompt (async)
    conversation_id = None
    try:
        conversation_id = await save_prompt(
            model=req.model,
            prompt=req.prompt,
            resp_text=full_text,
            conversation_title=req.conversation_title,
            conversation_id=None
        )
    except Exception as e:
        print("DB save error:", repr(e))
        traceback.print_exc()
        conversation_id = None

    return {
        "request_id": upstream_id or "ollama-agent",
        "model": req.model,
        "text": full_text,
        "tokens": tokens,
        "conversation_id": conversation_id,
        "conversation_title": req.conversation_title
    }

# -------------------------
# DB-backed endpoints (title-based)
# -------------------------

@app.get("/agent/data")
async def list_conversations(limit: int = Query(100, le=1000), offset: int = 0):
    try:
        convs = await get_conversations(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    return {"conversations": convs}

@app.get("/agent/data/messages")
async def conversation_messages(conversation_title: str = Query(...), limit: int = Query(200, le=2000), offset: int = 0):
    try:
        msgs = await get_messages_by_title(conversation_title=conversation_title, limit=limit, offset=offset)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    return {"conversation_title": conversation_title, "messages": msgs}

@app.get("/agent/data/last")
async def conversation_last(conversation_title: str = Query(...), n: int = Query(6, ge=1, le=200)):
    try:
        rows = await get_last_rows_by_title(conversation_title=conversation_title, limit=n)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    return {"conversation_title": conversation_title, "rows": rows}

@app.delete("/agent/data")
async def delete_conversation(conversation_title: str = Query(...)):
    try:
        deleted = await delete_conversation_by_title(conversation_title)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    return {"conversation_title": conversation_title, "deleted_rows": deleted}

@app.get("/agent/data/latest")
async def latest_conversation():
    try:
        latest = await get_latest_conversation_by_title()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    return {"latest": latest}
