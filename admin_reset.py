import os
import logging
import subprocess
import time
from fastapi import FastAPI, Header, HTTPException, status, BackgroundTasks, Request
from concurrent.futures import ThreadPoolExecutor
import asyncio

app = FastAPI()
API_KEY = os.environ.get("API_KEY", "")
RESET_SCRIPT = "/usr/local/bin/reset_agent.sh"
LOGFILE = "/opt/admin_reset/reset_agent_http.log"
RESET_COOLDOWN = 60  # sekuntia, mutta ilman kantaa käytetään vain muistissa

logger = logging.getLogger("reset")
logging.basicConfig(level=logging.INFO)

executor = ThreadPoolExecutor(max_workers=2)

# cooldown-muistiin (ei kantaa)
_last_reset_ts = 0


def check_api_key(provided: str) -> None:
    if (provided or "").strip() != API_KEY:
        logger.warning("Reset forbidden: provided != expected")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def append_log(text: str):
    try:
        with open(LOGFILE, "a") as fh:
            fh.write(text + "\n")
    except Exception:
        logger.exception("Failed to write reset log")


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


@app.post("/admin/reset")
async def admin_reset(request: Request, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    global _last_reset_ts

    check_api_key(x_api_key)

    now = time.time()
    if now - _last_reset_ts < RESET_COOLDOWN:
        raise HTTPException(status_code=429, detail="reset cooldown active")

    _last_reset_ts = now

    client_ip = request.client.host if request.client else "unknown"
    request_id = str(int(now * 1000))

    logger.info("Reset requested id=%s from=%s", request_id, client_ip)
    append_log(f"{now} RESET requested id={request_id} from={client_ip}")

    loop = asyncio.get_event_loop()

    def on_done(fut):
        rc, out, err = fut.result()
        append_log(f"RESET id={request_id} rc={rc}\nSTDOUT:\n{out}\nSTDERR:\n{err}")

    future = executor.submit(run_reset_script, 60)
    future.add_done_callback(on_done)

    return {"status": "accepted", "request_id": request_id}
