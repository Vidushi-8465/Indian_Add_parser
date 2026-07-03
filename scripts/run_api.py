"""Run the FastAPI search service."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn

from utils.constants import DEFAULT_APP_CONFIG
from utils.file_utils import load_yaml_config


def main() -> int:
    config = load_yaml_config(DEFAULT_APP_CONFIG)
    api_config = config.get("api", {})
    uvicorn.run(
        "api.main:app",
        host=api_config.get("host", "0.0.0.0"),
        port=int(api_config.get("port", 8000)),
        reload=bool(api_config.get("reload", False)),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
