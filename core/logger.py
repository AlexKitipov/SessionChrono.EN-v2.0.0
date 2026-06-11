"""Application logging infrastructure for SessionChrono.

The module exposes one configured application logger that writes persistent,
daily diagnostic logs to a user-writable directory resolved by ``core.config``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from .config import APP_NAME, APP_VERSION, IS_FROZEN, LOG_ROOT, runtime_path_report

LOGGER_NAME = APP_NAME
APP_LOG_DIR = LOG_ROOT / "application_logs"
_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_CONFIGURED = False


def current_log_file() -> Path:
    """Return today's diagnostic log file path."""

    return APP_LOG_DIR / f"{APP_NAME}_{datetime.now():%Y-%m-%d}.log"


def get_logger() -> logging.Logger:
    """Return the single configured SessionChrono application logger."""

    global _CONFIGURED

    logger = logging.getLogger(LOGGER_NAME)
    if _CONFIGURED:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    APP_LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(current_log_file(), encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(file_handler)

    _CONFIGURED = True
    return logger


def log_startup() -> None:
    """Record application startup and resolved runtime paths."""

    logger = get_logger()
    logger.info(
        "Starting %s %s (frozen=%s); diagnostic logs=%s",
        APP_NAME,
        APP_VERSION,
        IS_FROZEN,
        APP_LOG_DIR,
    )
    logger.info("Runtime path report: %s", runtime_path_report())


def log_shutdown() -> None:
    """Record application shutdown."""

    get_logger().info("Shutting down %s", APP_NAME)
