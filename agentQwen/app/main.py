# main.py
# version: 109
# QWEN agent API (controller)
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
import os, httpx
from typing import Optional

app = FastAPI(title="AI Agent 3 (qwen controller)")

QWEN_URL = os.getenv("QWEN_URL", "http://ollama:11434")  # docker-compose may override this

# --- IMPORTANT: register startup event ---
@app.on_event("startup")
async def startup_event():
    await init_db()

class GenReq(BaseModel):
    prompt: str
    conversation_title: str
    model: Optional[str] = None

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/generate")
async def generate(req: GenReq):
    """
    Generate a response from the QWEN model.
    The request MUST include conversation_title (user-provided).
    The prompt+response pair is saved to DB with conversation_title so the client
    can later list and open that conversation by title.
    Returns the response and the conversation_id used/created in DB.
    """
    if not req.prompt:
        raise HTTPException(status_code=400, detail="prompt required")
    if not req.conversation_title:
        raise HTTPException(status_code=400, detail="conversation_title required")

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
            # QWEN response structure: data["message"]["content"]
            text = data.get("message", {}).get("content", "")

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

    # Save prompt+response pair to DB with the provided conversation_title.
    # save_prompt returns the conversation_id used (new UUID if none provided).
    try:
        conversation_id = await save_prompt(
            model=resp.get("model", "unknown"),
            prompt=req.prompt,
            resp_text=resp.get("text", ""),
            conversation_title=req.conversation_title,
            conversation_id=None
        )
    except Exception as e:
        print("DB save error:", e)
        conversation_id = None

    # Return the conversation_title and conversation_id so proxy/client can continue the same conversation.
    return {
        **resp,
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
