import os
import time
import uuid
import hashlib
import httpx
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import aiomysql

from ndjson_parser import ensure_schema, assemble_ndjson_text_and_store, store_request_summary
import logging
from logging.handlers import RotatingFileHandler

LOG_PATH = "/opt/ollama_proxy/proxy_main.log"

logger = logging.getLogger("ollama_proxy_main")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)


DB = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "proxy",
    "password": "xxxx",
    "db": "ollama_proxy",
    "autocommit": True
}

async def get_conn():
    return await aiomysql.connect(**DB)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11435/api/generate")
IDLE_TIMEOUT = float(os.getenv("OLLAMA_IDLE_TIMEOUT", "5"))

app = FastAPI(title="Ollama Proxy Collector")

@app.on_event("startup")
async def startup():
    await ensure_schema()

@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
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
            async with client.stream("POST", OLLAMA_URL, json=body) as resp:
                upstream_status = resp.status_code
                if resp.status_code >= 400:
                    _ = await resp.aread()
                    raise HTTPException(status_code=502, detail=f"Upstream error: {resp.status_code}")

                full, tokens, done, idle_timed_out = await assemble_ndjson_text_and_store(
                    resp, req_id, idle_timeout=IDLE_TIMEOUT
                )
        except httpx.RequestError as e:
            logger.error(f"Upstream returned {resp.status_code} for {req_id}")
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {str(e)}")
            

    end = time.time()

    await store_request_summary(req_id, model, prompt_hash, start, end, tokens)

    prompt_preview = (prompt[:500] + "...") if len(prompt) > 500 else prompt

    result = {
        "request_id": req_id,
        "model": model,
        "tokens": tokens,
        "latency_ms": int((end - start) * 1000),
        "text": full,
        "done": bool(done),
        "idle_timed_out": bool(idle_timed_out),
        "prompt_preview": prompt_preview,
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
