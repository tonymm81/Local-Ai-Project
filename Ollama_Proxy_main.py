# /opt/ollama_proxy/main.py (vain relevantti osa)
import os
import time
import uuid
import hashlib
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from ndjson_parser import ensure_schema, assemble_ndjson_text_and_store, store_request_summary

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11435/api/generate")

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
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("POST", OLLAMA_URL, json=body) as resp:
                if resp.status_code >= 400:
                    text = await resp.aread()
                    raise HTTPException(status_code=502, detail=f"Upstream error: {resp.status_code}")
                full, tokens, done = await assemble_ndjson_text_and_store(resp, req_id)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {str(e)}")
    end = time.time()
    await store_request_summary(req_id, model, prompt_hash, start, end, tokens)
    return JSONResponse({
        "request_id": req_id,
        "model": model,
        "tokens": tokens,
        "latency_ms": int((end-start)*1000),
        "text": full
    })
