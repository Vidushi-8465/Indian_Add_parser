"""Application logging helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"

_CONFIGURED = False


def setup_logging(log_level: str = "INFO") -> None:
    """Configure loguru once for console and file output."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        enqueue=False,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{extra[module]}</cyan> - "
            "<level>{message}</level>"
        ),
    )
    logger.add(
        LOG_DIR / "app.log",
        level=log_level,
        rotation="10 MB",
        enqueue=False,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {extra[module]} - {message}",
    )
    _CONFIGURED = True


def get_logger(module: str):
    """Return a logger bound to a module name."""
    setup_logging()
    return logger.bind(module=module)
