import os
import time
import uuid
import hashlib
import httpx
import asyncio
from fastapi import FastAPI, Request, HTTPException, Path, Query
from fastapi.responses import JSONResponse
import aiomysql

from ndjson_parser import ensure_schema, assemble_ndjson_text_and_store, store_request_summary
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urljoin#version 109
import re

_SAFE_PATH_RE = re.compile(r"^/[-A-Za-z0-9_./%]*$")#version 109

def get_action_path(agent: str, action: str) -> str:#version 109
    if agent in AGENT_OVERRIDES and action in AGENT_OVERRIDES[agent]:
        return AGENT_OVERRIDES[agent][action]
    if action in AGENT_ENDPOINTS:
        return AGENT_ENDPOINTS[action]
    raise HTTPException(status_code=400, detail="Unknown action")

def compose_upstream(agent: str, path: str) -> str:#version 109
    base = AGENT_URLS.get(agent)
    if not base:
        raise HTTPException(status_code=400, detail="Unknown agent")
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


LOG_PATH = "/opt/ollama_proxy/proxy_main.log"

logger = logging.getLogger("ollama_proxy_main")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)

AGENT_URLS = {#version 109
    "pixatrail": os.getenv("OLLAMA_PIXATRAIL_URL", "http://127.0.0.1:7860"),
    "ollama-dev": os.getenv("OLLAMA_DEV_URL", "http://127.0.0.1:7861"),
    "ollama-qwen": os.getenv("OLLAMA_QWEN_URL", "http://127.0.0.1:11440"),
}

# Only the actions you actually use (no 'models' entry)
AGENT_ENDPOINTS = {#version 109
    "generate": "/api/generate",        # default
    "data_list": "/agent/data",
    "data_messages": "/agent/data/messages",
    "data_last": "/agent/data/last",
    "delete": "/agent/data"             # DELETE with ?conversation_title=...
}

# Per-agent overrides for actions that differ from the default
AGENT_OVERRIDES = {#version 109
    "pixatrail": { "generate": "/api/generate" },   # pixatrail uses /api/generate
    "ollama-dev": { "generate": "/generate" },      # dev agent uses /api/generate
    "ollama-qwen": { "generate": "/generate" }      # qwen uses /generate (no /api/)
}

def resolve_upstream(agent_name: str):
    if not agent_name:
        return None
    if agent_name not in AGENT_URLS:
        raise HTTPException(status_code=400, detail="Unknown agent")
    return AGENT_URLS[agent_name]


DB = {
    "host": os.getenv("OLLAMA_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("OLLAMA_DB_PORT", "3306")),
    "user": os.getenv("OLLAMA_DB_USER", "proxy"),
    "password": os.getenv("OLLAMA_DB_PASSWORD", ""),
    "db": os.getenv("OLLAMA_DB_NAME", "ollama_proxy"),
    "autocommit": True
}

# Validate at startup
if not DB["password"]:
    logger.error("Database password not set in OLLAMA_DB_PASSWORD")
    raise RuntimeError("Missing DB password environment variable OLLAMA_DB_PASSWORD")

async def get_conn():
    return await aiomysql.connect(**DB)


IDLE_TIMEOUT = float(os.getenv("OLLAMA_IDLE_TIMEOUT", "5"))

app = FastAPI(title="Ollama Proxy Collector")

@app.on_event("startup")
async def startup():
    await ensure_schema()

@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    agent = body.get("agent")
    if not agent:
        raise HTTPException(status_code=400, detail="agent required")

    # conversation_title from client (optional but forwarded and returned)
    conversation_title = body.get("conversation_title")

    # action or raw path selection (prefer action)
    action = body.get("action")
    client_path = body.get("path")

    # Decide path: prefer action, fallback to client_path, default to 'generate'
    if action:
        try:
            path = get_action_path(agent, action)
        except HTTPException:
            raise
    elif client_path:
        if not isinstance(client_path, str) or not client_path.startswith("/"):
            raise HTTPException(status_code=400, detail="path must start with '/'")
        if ".." in client_path or not _SAFE_PATH_RE.match(client_path):
            raise HTTPException(status_code=400, detail="invalid path")
        path = client_path
    else:
        path = get_action_path(agent, "generate")

    # Compose upstream URL safely
    upstream = compose_upstream(agent, path)

    # Ensure conversation_title is present in forwarded body if provided
    if conversation_title:
        body["conversation_title"] = conversation_title

    req_id = str(uuid.uuid4())
    model = body.get("model", "unknown")
    prompt = body.get("prompt", "")
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    start = time.time()
    full = ""
    tokens = 0
    done = False
    idle_timed_out = False
    upstream_status = None

    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("POST", upstream, json=body) as resp:
                upstream_status = resp.status_code
                if resp.status_code >= 400:
                    _ = await resp.aread()
                    raise HTTPException(status_code=502, detail=f"Upstream error: {resp.status_code}")

                full, tokens, done, idle_timed_out = await assemble_ndjson_text_and_store(
                    resp, req_id, idle_timeout=IDLE_TIMEOUT, agent=agent
                )
        except httpx.RequestError as e:
            logger.error(f"Upstream request failed for {req_id}: {e}")
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {str(e)}")

    end = time.time()

    # Try to include conversation_title in summary if store_request_summary supports it.
    # If it doesn't, this call should be adjusted to match your function signature.
    try:
        await store_request_summary(req_id, model, prompt_hash, start, end, tokens, agent=agent, conversation_title=conversation_title)
    except TypeError:
        # fallback: call without conversation_title if signature doesn't accept it
        await store_request_summary(req_id, model, prompt_hash, start, end, tokens, agent=agent)

    result = {
        "request_id": req_id,
        "model": model,
        "agent": agent,
        "conversation_title": conversation_title,
        "tokens": tokens,
        "latency_ms": int((end - start) * 1000),
        "text": full,
        "done": bool(done),
        "idle_timed_out": bool(idle_timed_out),
        "prompt_preview": (prompt[:500] + "...") if len(prompt) > 500 else prompt,
        "upstream_status": upstream_status
    }

    if idle_timed_out:
        return JSONResponse(result, status_code=502)

    return JSONResponse(result)


@app.get("/stats")
async def stats():
    conn = await get_conn()
    cur = await conn.cursor()

    await cur.execute("""
        SELECT COUNT(*), AVG(latency_ms), SUM(tokens),
               MIN(latency_ms), MAX(latency_ms)
        FROM requests
    """)

    row = await cur.fetchone()
    await cur.close()
    conn.close()

    return {
        "total_requests": int(row[0] or 0),
        "avg_latency_ms": float(row[1]) if row[1] is not None else None,
        "total_tokens": int(row[2] or 0),
        "min_latency_ms": int(row[3]) if row[3] is not None else None,
        "max_latency_ms": int(row[4]) if row[4] is not None else None
    }

@app.get("/requests/{request_id}")
async def get_request(request_id: str):
    conn = await get_conn()
    cur = await conn.cursor()

    await cur.execute("""
        SELECT request_id, model, prompt_hash, start_ts, end_ts, latency_ms, tokens
        FROM requests WHERE request_id=%s
    """, (request_id,))
    req = await cur.fetchone()

    if not req:
        await cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="request not found")

    await cur.execute("""
        SELECT ts, raw_line FROM events_raw
        WHERE request_id=%s ORDER BY id ASC
    """, (request_id,))
    events = await cur.fetchall()

    await cur.close()
    conn.close()

    return {
        "summary": {
            "request_id": req[0],
            "model": req[1],
            "prompt_hash": req[2],
            "start_ts": req[3],
            "end_ts": req[4],
            "latency_ms": req[5],
            "tokens": req[6]
        },
        "events": [{"ts": e[0], "raw_line": e[1]} for e in events]
    }



# Version 109 changes
@app.get("/proxy/{agent}/conversations")
async def list_conversations(agent: str = Path(...), limit: int = Query(100), offset: int = Query(0)):
    path = get_action_path(agent, "data_list")
    upstream = compose_upstream(agent, path)

    # Log upstream call
    logger.info("Proxying list_conversations agent=%s upstream=%s params=%s", agent, upstream, {"limit": limit, "offset": offset})

    async with httpx.AsyncClient() as client:
        resp = await client.get(upstream, params={"limit": limit, "offset": offset})

    # Log upstream response summary
    try:
        content_preview = (resp.text[:500] + "...") if len(resp.text) > 500 else resp.text
    except Exception:
        content_preview = "<unable to read response text>"
    logger.info("Upstream response for list_conversations agent=%s status=%s content_len=%d preview=%s",
                agent, resp.status_code, len(resp.content or b""), content_preview)

    try:
        content = resp.json()
    except Exception:
        content = resp.text
    return JSONResponse(status_code=resp.status_code, content=content)


@app.get("/proxy/{agent}/conversations/{conversation_title}/messages")
async def get_messages(
    agent: str = Path(...),
    conversation_title: str = Path(...),
    limit: int = Query(200),
    offset: int = Query(0)
):
    path = get_action_path(agent, "data_messages")
    upstream = compose_upstream(agent, path)

    # Log upstream call
    logger.info("Proxying get_messages agent=%s upstream=%s params=%s",
                agent, upstream, {"conversation_title": conversation_title, "limit": limit, "offset": offset})

    async with httpx.AsyncClient() as client:
        resp = await client.get(upstream, params={"conversation_title": conversation_title, "limit": limit, "offset": offset})

    # Log upstream response summary
    try:
        content_preview = (resp.text[:500] + "...") if len(resp.text) > 500 else resp.text
    except Exception:
        content_preview = "<unable to read response text>"
    logger.info("Upstream response for get_messages agent=%s status=%s content_len=%d preview=%s",
                agent, resp.status_code, len(resp.content or b""), content_preview)

    try:
        content = resp.json()
    except Exception:
        content = resp.text
    return JSONResponse(status_code=resp.status_code, content=content)


@app.delete("/proxy/{agent}/conversations/{conversation_title}")
async def delete_conversation(agent: str = Path(...), conversation_title: str = Path(...)):
    path = get_action_path(agent, "delete")
    upstream = compose_upstream(agent, path)

    # Log upstream call
    logger.info("Proxying delete_conversation agent=%s upstream=%s params=%s",
                agent, upstream, {"conversation_title": conversation_title})

    async with httpx.AsyncClient() as client:
        resp = await client.delete(upstream, params={"conversation_title": conversation_title})

    # Log upstream response summary
    try:
        content_preview = (resp.text[:500] + "...") if len(resp.text) > 500 else resp.text
    except Exception:
        content_preview = "<unable to read response text>"
    logger.info("Upstream response for delete_conversation agent=%s status=%s content_len=%d preview=%s",
                agent, resp.status_code, len(resp.content or b""), content_preview)

    try:
        content = resp.json()
    except Exception:
        content = resp.text
    return JSONResponse(status_code=resp.status_code, content=content)
