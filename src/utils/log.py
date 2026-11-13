import logging
from pathlib import Path

from paths import LOGS

LOG_DIR = LOGS
FORMAT = "%(asctime)s %(levelname)-7s %(name)-10s %(funcName)-12s %(message)s"

def get_logger(name: str) -> logging.Logger:
    """Logger that writes to console and logs/pipeline.log"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    LOG_DIR.mkdir(exist_ok=True)

    file = logging.FileHandler(LOG_DIR/"pipeline.log",encoding="utf-8")
    file.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file)
    return logger