import logging
import os
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()
API_KEY = os.environ.get("API_KEY", "")

def mask(k: str) -> str:
    if not k:
        return "<empty>"
    return k[:4] + "…" + k[-4:]

def repr_info(k: str) -> str:
    # näyttää repr ja pituuden
    return f"repr={repr(k)} len={len(k)}"

@app.post("/admin/reset")
def admin_reset(x_api_key: str = Header(None)):
    logging.info("DEBUG: expected key masked=%s %s", mask(API_KEY), repr_info(API_KEY))
    logging.info("DEBUG: received key masked=%s %s", mask(x_api_key), repr_info(x_api_key or ""))
    provided = (x_api_key or "").strip()
    logging.info("DEBUG: provided after strip repr=%s len=%d", repr(provided), len(provided))
    if provided != API_KEY:
        logging.warning("Reset forbidden: provided != expected")
        raise HTTPException(status_code=403, detail="forbidden")
    # jatka normaalisti reset-logiikkaan
    return {"status": "ok"}
