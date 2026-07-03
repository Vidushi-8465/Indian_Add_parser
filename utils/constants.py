"""Shared project constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INGESTION_CONFIG = PROJECT_ROOT / "configs" / "ingestion.yaml"
