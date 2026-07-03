"""Tests for the Phase 2 ingestion pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ingestion.merger import SchemaStandardizer
from ingestion.pipeline import IngestionPipeline
from ingestion.validator import DatasetValidator
from utils.string_utils import normalize_column_name


@pytest.fixture
def ingestion_config(tmp_path: Path) -> Path:
    raw_csv = tmp_path / "datasets" / "raw" / "csv"
    raw_excel = tmp_path / "datasets" / "raw" / "excel"
    master_dir = tmp_path / "datasets" / "master"
    raw_csv.mkdir(parents=True)
    raw_excel.mkdir(parents=True)
    master_dir.mkdir(parents=True)

    pincode_csv = raw_csv / "pincode_sample.csv"
    pincode_csv.write_text(
        "officename,pincode,district,statename,latitude,longitude\n"
        "Test Office,500001,Hyderabad,TELANGANA,17.385,78.486\n",
        encoding="utf-8",
    )

    city_csv = raw_csv / "city_sample.csv"
    city_csv.write_text(
        ",,,,,,\n"
        "Sl. No.,City/Town,Urban Status,State Code,State/ Union territory*,District Code,District\n"
        ",,,,,,\n"
        "1,Hyderabad,M.Corp,36,Telangana,123,Hyderabad\n",
        encoding="utf-8",
    )

    config = tmp_path / "ingestion.yaml"
    project_config = Path(__file__).resolve().parent.parent / "configs" / "ingestion.yaml"
    config.write_text(project_config.read_text(encoding="utf-8"), encoding="utf-8")
    config_text = config.read_text(encoding="utf-8")
    config_text = config_text.replace("datasets/raw/csv", "datasets/raw/csv")
    config.write_text(config_text, encoding="utf-8")

    updated = config.read_text(encoding="utf-8")
    updated = updated.replace('raw_csv_dir: datasets/raw/csv', f'raw_csv_dir: {raw_csv.as_posix()}')
    updated = updated.replace('raw_excel_dir: datasets/raw/excel', f'raw_excel_dir: {raw_excel.as_posix()}')
    updated = updated.replace('master_dataset: datasets/master/master_dataset.csv', f'master_dataset: {(master_dir / "master_dataset.csv").as_posix()}')
    updated = updated.replace('master_metadata: datasets/master/master_metadata.json', f'master_metadata: {(master_dir / "master_metadata.json").as_posix()}')
    config.write_text(updated, encoding="utf-8")
    return config


def test_normalize_column_name_variants() -> None:
    assert normalize_column_name("State Name (In English)") == "state name"
    assert normalize_column_name("State/ Union territory*") == "state union territory"
    assert normalize_column_name("PIN Code") == "pin code"


def test_schema_standardizer_maps_aliases() -> None:
    standardizer = SchemaStandardizer(
        standard_columns=["pincode", "state_name", "district_name", "source_file"],
        column_aliases={
            "pincode": ["pin code", "pincode"],
            "state_name": ["statename", "state name"],
            "district_name": ["district"],
        },
    )
    frame = pd.DataFrame(
        {
            "PIN Code": ["500001"],
            "statename": ["Telangana"],
            "district": ["Hyderabad"],
        }
    )
    result = standardizer.standardize(frame, "sample.csv")
    assert list(result.dataframe.columns) == ["pincode", "state_name", "district_name", "source_file"]
    assert result.dataframe.loc[0, "pincode"] == "500001"


def test_validator_rejects_empty_dataset() -> None:
    validator = DatasetValidator()
    result = validator.validate(pd.DataFrame(), "empty.csv")
    assert result.is_valid is False
    assert result.errors


def test_ingestion_pipeline_builds_master_dataset(ingestion_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_root = ingestion_config.parent
    monkeypatch.chdir(project_root)

    pipeline = IngestionPipeline(config_path=ingestion_config)
    metadata = pipeline.run()

    assert metadata["files_discovered"] == 2
    assert metadata["files_processed"] == 2
    assert metadata["total_rows"] == 2

    master_path = project_root / "datasets" / "master" / "master_dataset.csv"
    metadata_path = project_root / "datasets" / "master" / "master_metadata.json"
    assert master_path.exists()
    assert metadata_path.exists()

    master = pd.read_csv(master_path, dtype=str)
    assert "pincode" in master.columns
    assert "city_name" in master.columns
    assert len(master.index) == 2

    with metadata_path.open("r", encoding="utf-8") as handle:
        saved_metadata = json.load(handle)
    assert saved_metadata["pipeline"] == "ingestion"
    assert saved_metadata["files_processed"] == 2
