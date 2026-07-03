"""Quick script to preview CSV files in datasets/raw/csv."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.csv_loader import CSVLoader
from ingestion.header_detector import HeaderDetector
from app_logging.logger import setup_logging
from utils.constants import DEFAULT_INGESTION_CONFIG
from utils.file_utils import load_yaml_config

CSV_DIR = PROJECT_ROOT / "datasets" / "raw" / "csv"


def main() -> int:
    setup_logging()
    config = load_yaml_config(DEFAULT_INGESTION_CONFIG)
    header_detector = HeaderDetector(
        column_aliases=config["column_aliases"],
        max_scan_rows=config.get("reading", {}).get("max_header_scan_rows", 20),
    )
    loader = CSVLoader(
        header_detector=header_detector,
        encodings=config.get("reading", {}).get("encodings"),
    )

    files = sorted(CSV_DIR.glob("*.csv"))
    if not files:
        print(f"No CSV files found in {CSV_DIR}")
        return 0

    for file_path in files:
        print(f"\nReading: {file_path.name}")
        try:
            result = loader.load(file_path)
            print(f"Header row: {result.header_row + 1}")
            print(f"Encoding: {result.encoding}")
            print(f"Rows loaded: {len(result.dataframe.index)}")
            print(result.dataframe.head())
        except Exception as exc:
            print(f"ERROR: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
