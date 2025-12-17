import os
import time
import uuid
import hashlib
import httpx
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from ndjson_parser import ensure_schema, assemble_ndjson_text_and_store, store_request_summary

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11435/api/generate")
IDLE_TIMEOUT = float(os.getenv("OLLAMA_IDLE_TIMEOUT", "5"))  # sekunteina, ympäristömuuttujalla ylikirjoitettava

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

    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("POST", OLLAMA_URL, json=body) as resp:
                if resp.status_code >= 400:
                    # lue virheteksti upstreamilta (ei kaada)
                    _ = await resp.aread()
                    raise HTTPException(status_code=502, detail=f"Upstream error: {resp.status_code}")
                # kutsu parseria, joka sisältää idle timeoutin
                full, tokens, done, idle_timed_out = await assemble_ndjson_text_and_store(resp, req_id, idle_timeout=IDLE_TIMEOUT)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {str(e)}")

    end = time.time()
    # tallenna yhteenveto (tokens voi olla 0 jos timeout)
    await store_request_summary(req_id, model, prompt_hash, start, end, tokens)

    # jos tappokytkin laukeaa, palauta erillinen kenttä ja 502‑tyyppinen status jos haluat; tässä palautetaan 200 mutta merkitään timeout
    result = {
        "request_id": req_id,
        "model": model,
        "tokens": tokens,
        "latency_ms": int((end-start)*1000),
        "text": full,
        "done": bool(done),
        "idle_timed_out": bool(idle_timed_out)
    }
    # halutessasi voit muuttaa status‑koodin jos idle_timed_out on True:
    # if idle_timed_out: return JSONResponse(result, status_code=502)
    return JSONResponse(result)
