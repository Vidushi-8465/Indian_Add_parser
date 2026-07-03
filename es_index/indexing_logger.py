"""Configure dedicated indexing log output."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from utils.constants import PROJECT_ROOT

_INDEXING_LOG_CONFIGURED = False


def setup_indexing_logging(log_path: str | Path | None = None) -> None:
    """Attach an indexing-only log file sink."""
    global _INDEXING_LOG_CONFIGURED
    if _INDEXING_LOG_CONFIGURED:
        return

    path = Path(log_path or PROJECT_ROOT / "logs" / "indexing.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        path,
        level="INFO",
        enqueue=False,
        filter=lambda record: record["extra"].get("module", "").startswith("es_index"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {extra[module]} - {message}",
    )
    _INDEXING_LOG_CONFIGURED = True
