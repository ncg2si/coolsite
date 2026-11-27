import logging
import sys

from paths import LOGS, ON_DATABRICKS

LOG_DIR = LOGS
FORMAT = "%(asctime)s %(levelname)-7s %(name)-10s %(funcName)-12s %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Logger that writes to the console, and locally also to logs/pipeline.log.
    On Databricks only the console is used: notebook and job output keep the log,
    and nothing is written into the Git folder."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = (
        False  # avoid duplicate lines via the root logger (e.g. on Databricks)
    )
    formatter = logging.Formatter(FORMAT)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if not ON_DATABRICKS:
        LOG_DIR.mkdir(exist_ok=True)
        file = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
        file.setFormatter(formatter)
        logger.addHandler(file)
    return logger
