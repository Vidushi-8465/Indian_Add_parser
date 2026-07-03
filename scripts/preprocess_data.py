"""CLI entry point for Phase 3 preprocessing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from preprocessing.preprocessing_pipeline import PreprocessingPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the preprocessing pipeline on the master dataset.")
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "preprocessing.yaml",
        help="Path to preprocessing configuration file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("Starting preprocessing pipeline...", flush=True)
    print(f"Config: {args.config}", flush=True)
    print("Progress will appear below and in logs/app.log", flush=True)

    pipeline = PreprocessingPipeline(config_path=args.config)
    metadata = pipeline.run()

    stats = metadata["statistics"]
    print("Preprocessing completed successfully.")
    print(f"Rows in: {stats['rows_input']}")
    print(f"Rows out: {stats['rows_output']}")
    print(f"Duplicates removed: {stats['duplicate_rows_removed']}")
    print(f"Duplicate addresses removed: {stats['duplicate_addresses_removed']}")
    print(f"Empty rows removed: {stats['empty_rows_removed']}")
    print(f"Invalid pincodes: {stats['invalid_pincodes']}")
    print(f"Output: {metadata['output_dataset']}")
    print(f"Report: {metadata['preprocessing_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
