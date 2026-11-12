import logging
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "client.log"

logging.basicConfig(
    level=logging.DEBUG,
    format=(
        "%(asctime)s "
        "[%(levelname)s] "
        "[%(name)s] "
        "[%(funcName)s:%(lineno)d] "
        "%(message)s"
    ),
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        #logging.StreamHandler()
    ]
)

def get_logger(name: str):
    return logging.getLogger(name)