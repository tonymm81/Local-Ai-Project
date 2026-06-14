import os
import logging
import subprocess
import time
from fastapi import FastAPI, Header, HTTPException, status, BackgroundTasks, Request
from concurrent.futures import ThreadPoolExecutor
import aiosqlite
import asyncio

app = FastAPI()
API_KEY = os.environ.get("API_KEY", "")
RESET_SCRIPT = "/usr/local/bin/reset_agent.sh"
LOGFILE = "/var/log/reset_agent_http.log"
DB = "/var/lib/ollama_analytics/analytics.db"
RESET_COOLDOWN = 600  # seconds

logger = logging.getLogger("reset")
logging.basicConfig(level=logging.INFO)

executor = ThreadPoolExecutor(max_workers=2)

def check_api_key(provided: str) -> None:
    if (provided or "").strip() != API_KEY:
        logger.warning("Reset forbidden: provided != expected")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

def run_reset_script(timeout=60):
    try:
        proc = subprocess.run(
            ['sudo', RESET_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        return None, "", f"timeout: {e}"
    except Exception as e:
        return None, "", f"exec error: {e}"

async def can_trigger_reset(cooldown_seconds=RESET_COOLDOWN) -> bool:
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT ts FROM resets ORDER BY ts DESC LIMIT 1") as cur:
            row = await cur.fetchone()
            if not row:
                return True
            last = row[0]
            return (time.time() - last) > cooldown_seconds

async def record_reset(request_id: str, reason: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO resets(ts, request_id, reason) VALUES(?,?,?)",
            (time.time(), request_id, reason)
        )
        await db.commit()

def append_log(text: str):
    try:
        with open(LOGFILE, "a") as fh:
            fh.write(text + "\n")
    except Exception:
        logger.exception("Failed to write reset log")

@app.post("/admin/reset")
async def admin_reset(request: Request, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    check_api_key(x_api_key)
    client_ip = request.client.host if request.client else "unknown"
    request_id = str(int(time.time()*1000))

    if not await can_trigger_reset():
        raise HTTPException(status_code=429, detail="reset cooldown active")

    logger.info("Reset requested id=%s from=%s", request_id, client_ip)
    append_log(f"{time.time()} RESET requested id={request_id} from={client_ip}")

    loop = asyncio.get_event_loop()

    def on_done(fut):
        rc, out, err = fut.result()
        append_log(f"RESET id={request_id} rc={rc}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
        loop.call_soon_threadsafe(asyncio.create_task, record_reset(request_id, "manual"))

    future = executor.submit(run_reset_script, 60)
    future.add_done_callback(on_done)

    return {"status": "accepted", "request_id": request_id}
