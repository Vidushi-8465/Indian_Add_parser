"""CLI entry point for Phase 2 data ingestion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.pipeline import IngestionPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Phase 2 data ingestion pipeline.")
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "ingestion.yaml",
        help="Path to the ingestion configuration file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pipeline = IngestionPipeline(config_path=args.config)
    metadata = pipeline.run()

    print("Ingestion completed successfully.")
    print(f"Files discovered: {metadata['files_discovered']}")
    print(f"Files processed: {metadata['files_processed']}")
    print(f"Files failed: {metadata['files_failed']}")
    print(f"Total rows: {metadata['total_rows']}")
    print(f"Master dataset: {metadata['output_dataset']}")
    print(f"Metadata file: {metadata['output_metadata']}")

    if metadata["validation_errors"]:
        print("\nValidation errors:")
        for error in metadata["validation_errors"]:
            print(f"  - {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
