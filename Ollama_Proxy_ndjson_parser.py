import json
import time
import aiosqlite
import asyncio
from typing import Tuple

DB = "/var/lib/ollama_analytics/analytics.db"

async def ensure_schema():
    async with aiosqlite.connect(DB) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute(""" CREATE TABLE IF NOT EXISTS requests(
            request_id TEXT PRIMARY KEY,
            model TEXT,
            prompt_hash TEXT,
            start_ts REAL,
            end_ts REAL,
            latency_ms INTEGER,
            tokens INTEGER
        )""")
        await db.execute(""" CREATE TABLE IF NOT EXISTS events_raw(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT,
            ts REAL,
            raw_line TEXT
        )""")
        await db.execute(""" CREATE INDEX IF NOT EXISTS idx_events_raw_request_id ON events_raw(request_id) """)
        await db.execute(""" CREATE TABLE IF NOT EXISTS resets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL,
            request_id TEXT,
            reason TEXT
        ) """)
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

async def assemble_ndjson_text_and_store(resp, request_id: str, idle_timeout: float = 5.0) -> Tuple[str,int,bool,bool]:
    """
    Kokoa NDJSON‑streamista tekstiä ja tallenna rivit DB:hen.
    Palauttaa: (full_text, tokens, done_flag, idle_timed_out_flag)
    idle_timeout = sekunteina; jos ei tule uutta chunkia tämän ajan, funktio lopettaa.
    """
    parts = []
    tokens = 0
    done = False
    idle_timed_out = False

    ait = resp.aiter_text()

    while True:
        try:
            # odota seuraavaa chunkia, mutta aikakatkaise jos ei tule
            raw = await asyncio.wait_for(ait.__anext__(), timeout=idle_timeout)
        except asyncio.TimeoutError:
            # ei tullut uutta dataa määritettyyn aikaan -> tappokytkin laukeaa
            idle_timed_out = True
            break
        except StopAsyncIteration:
            # stream päättyi normaalisti
            break
        if not raw:
            continue
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            # tallenna raakarivi
            try:
                await store_raw_line(request_id, line)
            except Exception:
                # älä kaada koko prosessia DB‑virheestä; jatka
                pass
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

    clean_parts = [p.strip() for p in parts if p and p.strip()] 
    full = " ".join(clean_parts) # käyttää välilyöntiä, estää sanojen rivittymisen
    return full, tokens, done, idle_timed_out
