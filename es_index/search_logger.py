"""Search query logging."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from utils.constants import PROJECT_ROOT

_SEARCH_LOG_CONFIGURED = False


def setup_search_logging(log_path: str | Path | None = None) -> None:
    """Attach a search-only log file sink."""
    global _SEARCH_LOG_CONFIGURED
    if _SEARCH_LOG_CONFIGURED:
        return

    path = Path(log_path or PROJECT_ROOT / "logs" / "search.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        path,
        level="INFO",
        enqueue=False,
        filter=lambda record: "search" in record["extra"].get("module", ""),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {extra[module]} - {message}",
    )
    _SEARCH_LOG_CONFIGURED = True


class SearchLogger:
    """Structured search request/response logging."""

    def __init__(self) -> None:
        setup_search_logging()
        self.logger = logger.bind(module="es_index.search")

    def log_search(
        self,
        strategy: str,
        request: dict[str, Any],
        response_summary: dict[str, Any],
    ) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy": strategy,
            "request": request,
            "response": response_summary,
        }
        self.logger.info("search_event {}", json.dumps(payload, ensure_ascii=False))
