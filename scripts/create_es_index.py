"""Create the indian_addresses Elasticsearch index."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app_logging.logger import setup_logging
from es_index.client import build_elasticsearch_client, test_connection
from es_index.index_manager import IndexManager
from utils.constants import DEFAULT_ELASTICSEARCH_CONFIG
from utils.file_utils import load_yaml_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the indian_addresses Elasticsearch index.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_ELASTICSEARCH_CONFIG,
        help="Path to elasticsearch configuration file.",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate the index if it already exists.",
    )
    return parser.parse_args()


def main() -> int:
    setup_logging()
    args = parse_args()
    config = load_yaml_config(args.config)
    client = build_elasticsearch_client(config)

    if not test_connection(client=client, config=config)["connected"]:
        print("ERROR: Elasticsearch is not reachable at configured host.", flush=True)
        return 1

    manager = IndexManager(client, config)
    result = manager.create_index(recreate=args.recreate)
    stats = manager.get_index_stats()

    print(f"Index: {result['index']}")
    print(f"Created: {result['created']}")
    print(f"Documents: {stats.get('document_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
