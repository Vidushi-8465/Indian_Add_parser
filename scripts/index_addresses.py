"""Bulk index final_clean_dataset.csv into Elasticsearch."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from es_index.indexing_pipeline import IndexingPipeline
from utils.constants import DEFAULT_ELASTICSEARCH_CONFIG


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index cleaned addresses into Elasticsearch.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_ELASTICSEARCH_CONFIG,
        help="Path to elasticsearch configuration file.",
    )
    parser.add_argument(
        "--recreate-index",
        action="store_true",
        help="Delete and recreate the index before indexing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("Starting Elasticsearch indexing...", flush=True)
    print("Progress will appear below and in logs/indexing.log", flush=True)

    pipeline = IndexingPipeline(config_path=args.config)
    metadata = pipeline.run(recreate_index=args.recreate_index)

    stats = metadata["statistics"]
    print("Indexing completed successfully.", flush=True)
    print(f"Rows read: {stats['rows_read']}")
    print(f"Documents indexed: {stats['indexed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Elapsed seconds: {stats['elapsed_seconds']}")
    print(f"Indexing report: {metadata['indexing_report']}")
    print(f"Performance report: {metadata['performance_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
