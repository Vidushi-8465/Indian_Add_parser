"""Tests for the Phase 2 ingestion pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ingestion.header_detector import HeaderDetector
from ingestion.merger import SchemaStandardizer
from ingestion.pipeline import IngestionPipeline
from ingestion.validator import DatasetValidator
from app_logging.logger import setup_logging
from utils.string_utils import is_subdistrict_column, normalize_column_name


@pytest.fixture
def ingestion_config(tmp_path: Path) -> Path:
    raw_csv = tmp_path / "datasets" / "raw" / "csv"
    master_dir = tmp_path / "datasets" / "master"
    raw_csv.mkdir(parents=True)
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
    updated = project_config.read_text(encoding="utf-8")
    updated = updated.replace("raw_data_dir: datasets/raw/csv", f"raw_data_dir: {raw_csv.as_posix()}")
    updated = updated.replace(
        "master_dataset: datasets/master/master_dataset.csv",
        f"master_dataset: {(master_dir / 'master_dataset.csv').as_posix()}",
    )
    updated = updated.replace(
        "master_metadata: datasets/master/master_metadata.json",
        f"master_metadata: {(master_dir / 'master_metadata.json').as_posix()}",
    )
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


def test_subdistrict_columns_do_not_map_to_district() -> None:
    project_config = Path(__file__).resolve().parent.parent / "configs" / "ingestion.yaml"
    from utils.file_utils import load_yaml_config

    config = load_yaml_config(project_config)
    standardizer = SchemaStandardizer(
        standard_columns=config["standard_columns"],
        column_aliases=config["column_aliases"],
    )
    frame = pd.DataFrame(
        {
            "District Code": ["603"],
            "District Name (In English)": ["Nicobars"],
            "Subdistrict Code": ["5916"],
            "Subdistrict Name (In English)": ["Car Nicobar"],
            "SubDistrict Code": ["5917"],
            "SubDistrict Name": ["Other Tehsil"],
        }
    )
    result = standardizer.standardize(frame, "gps.csv")

    assert result.column_mapping["District Code"] == "district_code"
    assert result.column_mapping["District Name (In English)"] == "district_name"
    assert result.column_mapping["Subdistrict Code"] == "subdistrict_code"
    assert result.column_mapping["Subdistrict Name (In English)"] == "subdistrict_name"
    assert result.column_mapping["SubDistrict Code"] == "subdistrict_code"
    assert result.column_mapping["SubDistrict Name"] == "subdistrict_name"
    assert result.dataframe.loc[0, "district_code"] == "603"
    assert result.dataframe.loc[0, "subdistrict_code"] == "5916"


def test_is_subdistrict_column_marker() -> None:
    assert is_subdistrict_column("subdistrict code")
    assert is_subdistrict_column("sub-district name")
    assert not is_subdistrict_column("district code")


def test_validator_rejects_empty_dataset() -> None:
    validator = DatasetValidator()
    result = validator.validate(pd.DataFrame(), "empty.csv")
    assert result.is_valid is False
    assert result.errors


def test_header_detector_selects_alias_row() -> None:
    setup_logging()
    project_config = Path(__file__).resolve().parent.parent / "configs" / "ingestion.yaml"
    from utils.file_utils import load_yaml_config

    config = load_yaml_config(project_config)
    detector = HeaderDetector(column_aliases=config["column_aliases"], max_scan_rows=20)

    preview = pd.DataFrame(
        [
            ["All Development Blocks of India with covered villages", "", "", ""],
            ["S.No.", "State Code", "State Name (In English)", "pincode"],
            ["1", "35", "Andaman And Nicobar Islands", "744101"],
        ]
    )
    result = detector.detect(preview, source_file="blocks.csv")
    assert result.header_row == 1
    assert result.score > 0
    assert "state code" in result.matched_aliases
    assert "pincode" in result.matched_aliases


def test_header_detector_skips_blank_rows() -> None:
    project_config = Path(__file__).resolve().parent.parent / "configs" / "ingestion.yaml"
    from utils.file_utils import load_yaml_config

    config = load_yaml_config(project_config)
    detector = HeaderDetector(column_aliases=config["column_aliases"], max_scan_rows=20)

    preview = pd.DataFrame(
        [
            ["", "", "", "", "", ""],
            ["Sl. No.", "City/Town", "Urban Status", "State Code", "State/ Union territory*", "District"],
            ["", "", "", "", "", ""],
            ["1", "Hyderabad", "M.Corp", "36", "Telangana", "Hyderabad"],
        ]
    )
    result = detector.detect(preview, source_file="cities.csv")
    assert result.header_row == 1
    assert "city town" in result.matched_aliases or "sl no" in result.matched_aliases


def test_ingestion_pipeline_builds_master_dataset(ingestion_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_root = ingestion_config.parent
    monkeypatch.chdir(project_root)

    pipeline = IngestionPipeline(config_path=ingestion_config)
    metadata = pipeline.run()

    assert metadata["files_discovered"] == 2
    assert metadata["files_processed"] == 2
    assert metadata["total_rows"] == 2
    assert metadata["input_format"] == "csv"

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
