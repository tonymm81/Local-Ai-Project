import json
import time
import aiomysql
import asyncio
from typing import Tuple

import logging
from logging.handlers import RotatingFileHandler

LOG_PATH = "/opt/ollama_proxy/ndJsonParser.log"

logger = logging.getLogger("ollama_proxy")
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

async def ensure_schema():
    conn = None
    cur = None
    try:
        conn = await get_conn()
        cur = await conn.cursor()

        await cur.execute("""
            CREATE TABLE IF NOT EXISTS requests(
                request_id VARCHAR(64) PRIMARY KEY,
                model VARCHAR(255),
                prompt_hash VARCHAR(255),
                start_ts DOUBLE,
                end_ts DOUBLE,
                latency_ms INT,
                tokens INT,
                agent VARCHAR(64)
            )
        """)

        await cur.execute("""
            CREATE TABLE IF NOT EXISTS events_raw(
                id INT AUTO_INCREMENT PRIMARY KEY,
                request_id VARCHAR(64),
                ts DOUBLE,
                raw_line LONGTEXT
            )
        """)

        await cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_raw_request_id
            ON events_raw(request_id)
        """)

        await cur.execute("""
            CREATE TABLE IF NOT EXISTS resets(
                id INT AUTO_INCREMENT PRIMARY KEY,
                ts DOUBLE,
                request_id VARCHAR(64),
                reason TEXT
            )
        """)

        await conn.commit()

    except Exception as e:
        logger.error(f"ensure_schema() failed: {e}")

    finally:
        if cur:
            await cur.close()
        if conn:
            conn.close()


async def store_raw_line(request_id: str, raw_line: str):
    try:
        conn = await get_conn()
        cur = await conn.cursor()
        await cur.execute(
            "INSERT INTO events_raw(request_id, ts, raw_line) VALUES(%s, %s, %s)",
            (request_id, time.time(), raw_line)
        )
        await cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"store_raw_line() failed for {request_id}: {e}")

async def store_request_summary(request_id: str, model: str, prompt_hash: str, start_ts: float, end_ts: float, tokens: int, agent: str = None):
    try:
        latency_ms = int((end_ts - start_ts) * 1000) if (start_ts is not None and end_ts is not None) else None
        conn = await get_conn()
        cur = await conn.cursor()
        await cur.execute(
            """INSERT INTO requests(request_id, model, prompt_hash, start_ts, end_ts, latency_ms, tokens, agent)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                 model=VALUES(model),
                 prompt_hash=VALUES(prompt_hash),
                 start_ts=VALUES(start_ts),
                 end_ts=VALUES(end_ts),
                 latency_ms=VALUES(latency_ms),
                 tokens=VALUES(tokens),
                 agent=VALUES(agent)
            """,
            (request_id, model, prompt_hash, start_ts, end_ts, latency_ms, tokens, agent)
        )
        await cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"store_request_summary() failed for {request_id}: {e}")

async def assemble_ndjson_text_and_store(resp, request_id: str, idle_timeout: float = 5.0, agent: str = None) -> Tuple[str,int,bool,bool]:
    parts = []
    tokens = 0
    done = False
    idle_timed_out = False

    ait = resp.aiter_text()

    # Luetaan streamiä; jos upstream ei streamaa ndjson:ia vaan palauttaa yhden JSON-objektin, käsitellään se
    buffer = ""
    while True:
        try:
            raw = await asyncio.wait_for(ait.__anext__(), timeout=idle_timeout)
        except asyncio.TimeoutError:
            idle_timed_out = True
            break
        except StopAsyncIteration:
            break

        if not raw:
            continue

        buffer += raw
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue

            # Tallenna raaka rivi
            try:
                await store_raw_line(request_id, line)
            except Exception:
                pass

            # Yritä parsia JSON-rivi
            try:
                obj = json.loads(line)
            except Exception:
                # Ei JSON-riviä, lisää suoraan
                parts.append(line)
                tokens += len(line.split())
                continue
            # Jos obj on dict ja sisältää response tai text
            if isinstance(obj, dict):
                resp_fragment = obj.get("response") or obj.get("text") or ""
                if isinstance(resp_fragment, str) and resp_fragment:
                    parts.append(resp_fragment)
                    tokens += len(resp_fragment.split())
                if obj.get("done") is True:
                    done = True
            else:
                # jos obj ei ole dict, lisää sen stringinä
                s = json.dumps(obj)
                parts.append(s)
                tokens += len(s.split())

    # Jos buffer sisältää yhden JSON-objektin (ei ndjson stream), yritä parsia koko buffer
    if not parts and buffer:
        try:
            whole = json.loads(buffer)
            if isinstance(whole, dict):
                resp_fragment = whole.get("response") or whole.get("text") or ""
                if resp_fragment:
                    parts.append(resp_fragment)
                    tokens += len(resp_fragment.split())
                if whole.get("done") is True:
                    done = True
                # tallenna koko raw buffer
                try:
                    await store_raw_line(request_id, buffer)
                except Exception:
                    pass
        except Exception:
            # ei JSON, jätä bufferin teksti osaksi parts
            parts.append(buffer)
            tokens += len(buffer.split())

    clean_parts = [p.strip() for p in parts if p and p.strip()]
    full = " ".join(clean_parts)
    return full, tokens, done, idle_timed_out