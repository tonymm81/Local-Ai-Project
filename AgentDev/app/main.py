# main.py
# version: 109
# Dev agent API (Ollama dev controller)
# - Uses conversation_title as the primary key for conversation operations
# - Adds DB-backed conversation endpoints:
#   GET  /agent/data                     -> list conversations (by title)
#   GET  /agent/data/messages            -> get messages for a conversation (by title)
#   GET  /agent/data/last                -> get last N prompt/response rows for a conversation (by title)
#   DELETE /agent/data                   -> delete conversation by title
#   GET  /agent/data/latest              -> get latest conversation (by title)
# - Keeps existing /generate route but requires conversation_title in request body
# - Comments in English

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from db import (
    save_prompt,
    init_db,
    get_conversations,
    get_messages_by_title,
    get_last_rows_by_title,
    delete_conversation_by_title,
    get_latest_conversation_by_title
)
import httpx
import os
from typing import Optional

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

app = FastAPI(title="Ollama Dev Agent")

# --- IMPORTANT: register startup event ---
@app.on_event("startup")
async def startup_event():
    await init_db()

class GenReq(BaseModel):
    prompt: str
    conversation_title: str
    model: Optional[str] = "phi_2_gguf:latest"

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/generate")
async def generate(req: GenReq):
    """
    Stream upstream response but buffer it locally.
    Parse NDJSON chunks to extract only the textual 'response'/'text' fields
    and save to DB only after the upstream stream completes.
    """
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
    conversation_id = None
    upstream_id = None

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/generate", json=payload) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    body_text = body.decode("utf-8", errors="replace") if body else "<no body>"
                    raise HTTPException(status_code=500, detail=f"Ollama HTTP {resp.status_code}: {body_text}")

                # Buffer partial line fragments between chunks
                line_buf = ""

                async for chunk in resp.aiter_text():
                    if not chunk:
                        continue

                    line_buf += chunk
                    lines = line_buf.split("\n")

                    # If last char wasn't newline, keep the last partial line in buffer
                    if not line_buf.endswith("\n"):
                        line_buf = lines.pop()
                    else:
                        line_buf = ""

                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        # Try to parse JSON line (NDJSON style)
                        try:
                            import json as _json
                            parsed = _json.loads(line)
                            candidate = None
                            if isinstance(parsed, dict):
                                # common fields
                                candidate = parsed.get("response") or parsed.get("text")
                                # nested message content (qwen style)
                                if not candidate and isinstance(parsed.get("message"), dict):
                                    candidate = parsed["message"].get("content")
                                # capture upstream id if present
                                if parsed.get("id"):
                                    upstream_id = parsed.get("id")
                            if candidate:
                                full_text += candidate
                            else:
                                # ignore pure metadata lines (done/context) but keep spacing
                                full_text += " "
                        except Exception:
                            # Not JSON: append raw line content
                            full_text += line + " "

                # After stream ends, handle any leftover partial line
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

                # Some upstreams may include a final JSON body; try to read and prefer it
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
                    # ignore parse errors and keep assembled full_text
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

    # Save to SQLite with conversation_title (required) AFTER stream completed
    try:
        conversation_id = await save_prompt(
            model=req.model,
            prompt=req.prompt,
            resp_text=full_text,
            conversation_title=req.conversation_title,
            conversation_id=None
        )
    except Exception as e:
        print("DB save error:", e)
        conversation_id = None

    return {
        "request_id": upstream_id or "ollama-dev",
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
    """
    Return a list of conversations grouped by conversation_title.
    Each item: { conversation_title, last_updated, message_count }.
    """
    try:
        convs = await get_conversations(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    return {"conversations": convs}

@app.get("/agent/data/messages")
async def conversation_messages(conversation_title: str = Query(...), limit: int = Query(200, le=2000), offset: int = 0):
    """
    Return messages for a given conversation_title in chronological order (oldest -> newest).
    Each row contains prompt_text and response_text.
    """
    try:
        msgs = await get_messages_by_title(conversation_title=conversation_title, limit=limit, offset=offset)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    return {"conversation_title": conversation_title, "messages": msgs}

@app.get("/agent/data/last")
async def conversation_last(conversation_title: str = Query(...), n: int = Query(6, ge=1, le=200)):
    """
    Return the last n prompt/response rows for a conversation_title (chronological order).
    Useful for building agent context.
    """
    try:
        rows = await get_last_rows_by_title(conversation_title=conversation_title, limit=n)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    return {"conversation_title": conversation_title, "rows": rows}

@app.delete("/agent/data")
async def delete_conversation(conversation_title: str = Query(...)):
    """
    Delete all rows that match the given conversation_title.
    Returns the number of deleted rows.
    Deletion is by title as requested (no id-based delete function).
    """
    try:
        deleted = await delete_conversation_by_title(conversation_title)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    return {"conversation_title": conversation_title, "deleted_rows": deleted}

@app.get("/agent/data/latest")
async def latest_conversation():
    """
    Return the most recently updated conversation by title (conversation_title, last_updated),
    or null if none exist.
    """
    try:
        latest = await get_latest_conversation_by_title()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    return {"latest": latest}
