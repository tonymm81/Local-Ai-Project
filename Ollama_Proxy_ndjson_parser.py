# /opt/ollama_proxy/ndjson_parser.py
import json
import time
import aiosqlite
from typing import Tuple

DB = "/var/lib/ollama_analytics/analytics.db"

async def ensure_schema():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS requests(
            request_id TEXT PRIMARY KEY,
            model TEXT,
            prompt_hash TEXT,
            start_ts REAL,
            end_ts REAL,
            latency_ms INTEGER,
            tokens INTEGER
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS events_raw(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT,
            ts REAL,
            raw_line TEXT
        )""")
        await db.commit()

async def store_raw_line(request_id: str, raw_line: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO events_raw(request_id, ts, raw_line) VALUES(?,?,?)",
            (request_id, time.time(), raw_line)
        )
        await db.commit()

async def store_request_summary(request_id: str, model: str, prompt_hash: str, start_ts: float, end_ts: float, tokens: int):
    latency_ms = int((end_ts - start_ts) * 1000)
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO requests(request_id, model, prompt_hash, start_ts, end_ts, latency_ms, tokens) VALUES(?,?,?,?,?,?,?)",
            (request_id, model, prompt_hash, start_ts, end_ts, latency_ms, tokens)
        )
        await db.commit()

async def assemble_ndjson_text_and_store(resp, request_id: str) -> Tuple[str,int,bool]:
    parts = []
    tokens = 0
    done = False
    async for raw in resp.aiter_text():
        if not raw:
            continue
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            await store_raw_line(request_id, line)
            try:
                obj = json.loads(line)
            except Exception:
                parts.append(line)
                tokens += len(line.split())
                continue
            if isinstance(obj.get("response"), str):
                parts.append(obj["response"])
                tokens += len(obj["response"].split())
            if obj.get("done") is True:
                done = True
    full = "".join(parts)
    return full, tokens, done
