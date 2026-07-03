"""Shared project constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INGESTION_CONFIG = PROJECT_ROOT / "configs" / "ingestion.yaml"
DEFAULT_PREPROCESSING_CONFIG = PROJECT_ROOT / "configs" / "preprocessing.yaml"
DEFAULT_ELASTICSEARCH_CONFIG = PROJECT_ROOT / "configs" / "elasticsearch.yaml"
DEFAULT_APP_CONFIG = PROJECT_ROOT / "configs" / "app.yaml"
