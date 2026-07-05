"""Test Elasticsearch connection using .env credentials."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app_logging.logger import setup_logging
from es_index.client import build_elasticsearch_client, test_connection
from utils.constants import DEFAULT_ELASTICSEARCH_CONFIG
from utils.file_utils import load_yaml_config


def main() -> int:
    setup_logging()
    config = load_yaml_config(DEFAULT_ELASTICSEARCH_CONFIG)
    client = build_elasticsearch_client(config)
    status = test_connection(client=client, config=config)

    print(json.dumps(status, indent=2), flush=True)
    return 0 if status["connected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
