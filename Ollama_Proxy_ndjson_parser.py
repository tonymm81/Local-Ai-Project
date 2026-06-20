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
                tokens INT
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
        latency_ms = int((end_ts - start_ts) * 1000)
        conn = await get_conn()
        cur = await conn.cursor()
        ...
        await cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"store_request_summary() failed for {request_id}: {e}")

async def store_request_summary(request_id: str, model: str, prompt_hash: str, start_ts: float, end_ts: float, tokens: int):
    latency_ms = int((end_ts - start_ts) * 1000)
    conn = await get_conn()
    cur = await conn.cursor()
    await cur.execute(
        """INSERT INTO requests(request_id, model, prompt_hash, start_ts, end_ts, latency_ms, tokens)
           VALUES(%s,%s,%s,%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE
             model=VALUES(model),
             prompt_hash=VALUES(prompt_hash),
             start_ts=VALUES(start_ts),
             end_ts=VALUES(end_ts),
             latency_ms=VALUES(latency_ms),
             tokens=VALUES(tokens)
        """,
        (request_id, model, prompt_hash, start_ts, end_ts, latency_ms, tokens)
    )
    await cur.close()
    conn.close()

async def assemble_ndjson_text_and_store(resp, request_id: str, idle_timeout: float = 5.0) -> Tuple[str,int,bool,bool]:
    parts = []
    tokens = 0
    done = False
    idle_timed_out = False

    ait = resp.aiter_text()

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

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue

            try:
                await store_raw_line(request_id, line)
            except Exception:
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
    full = " ".join(clean_parts)
    return full, tokens, done, idle_timed_out
