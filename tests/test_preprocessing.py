"""Tests for the preprocessing pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from preprocessing.abbreviation_expander import AbbreviationExpander
from preprocessing.address_builder import AddressBuilder
from preprocessing.address_deduplicator import AddressDeduplicator
from preprocessing.address_validator import AddressValidator
from preprocessing.cleaner import DataCleaner
from preprocessing.deduplicator import Deduplicator
from preprocessing.normalizer import AddressNormalizer
from preprocessing.null_handler import NullHandler
from preprocessing.preprocessing_pipeline import PreprocessingPipeline
from preprocessing.quality_scorer import QualityScorer
from preprocessing.searchable_text_builder import SearchableTextBuilder
from preprocessing.statistics import DatasetStatistics
from preprocessing.symbol_normalizer import SymbolNormalizer
from utils.hash_utils import compute_address_hash
from utils.string_utils import normalize_for_deduplication


def test_null_handler_converts_null_like_values() -> None:
    handler = NullHandler()
    frame = pd.DataFrame({"state_name": ["NULL", "None", "NA", "Maharashtra"]})
    result = handler.normalize_nulls(frame, ["state_name"])
    assert pd.isna(result.loc[0, "state_name"])
    assert pd.isna(result.loc[1, "state_name"])
    assert pd.isna(result.loc[2, "state_name"])
    assert result.loc[3, "state_name"] == "Maharashtra"


def test_deduplicator_removes_duplicate_rows() -> None:
    frame = pd.DataFrame(
        {
            "pincode": ["500001", "500001", "500002"],
            "state_name": ["Telangana", "Telangana", "Telangana"],
        }
    )
    deduped, removed = Deduplicator().remove_duplicates(frame)
    assert removed == 1
    assert len(deduped.index) == 2


def test_address_deduplicator_treats_punctuation_variants_as_one() -> None:
    frame = pd.DataFrame({"full_address": ["TCS Hinjewadi", "TCS, Hinjewadi", "Infosys Pune"]})
    enriched = AddressDeduplicator().add_address_hash(frame)
    deduped, removed = AddressDeduplicator().remove_address_duplicates(enriched)
    assert removed == 1
    assert len(deduped.index) == 2
    assert enriched.loc[0, "address_hash"] == enriched.loc[1, "address_hash"]


def test_normalize_for_deduplication() -> None:
    assert normalize_for_deduplication("TCS, Hinjewadi") == normalize_for_deduplication("TCS Hinjewadi")


def test_symbol_normalizer_cleans_sector_dash_pattern() -> None:
    frame = pd.DataFrame({"locality": ["sector - 21", "Block#A"]})
    result = SymbolNormalizer().normalize(frame, ["locality"])
    assert result.loc[0, "locality"] == "sector 21"


def test_searchable_text_builder_combines_fields() -> None:
    frame = pd.DataFrame(
        {
            "building_name": ["TCS"],
            "road_name": ["Rajiv Gandhi Infotech Park"],
            "locality": ["Hinjewadi"],
            "city_name": ["Pune"],
            "state_name": ["Maharashtra"],
            "pincode": ["411057"],
        }
    )
    result = SearchableTextBuilder().build(frame)
    text = result.loc[0, "searchable_text"]
    assert "tcs" in text
    assert "hinjewadi" in text
    assert "411057" in text


def test_address_validator_removes_rows_without_pincode_or_coordinates() -> None:
    frame = pd.DataFrame(
        {
            "full_address": ["TCS, Hinjewadi, Pune, Maharashtra, 411057", "Bad, Bad, Bad"],
            "address_hash": ["hash-a", "hash-b"],
            "locality": ["Hinjewadi", "Bad"],
            "city_name": ["Pune", "Bad"],
            "district_name": ["Pune", "Bad"],
            "state_name": ["Maharashtra", "Bad"],
            "pincode": ["411057", pd.NA],
            "latitude": ["18.59", pd.NA],
            "longitude": ["73.73", pd.NA],
            "quality_score": [80.0, 80.0],
        }
    )
    filtered, removed = AddressValidator().filter_invalid_addresses(
        frame,
        {
            "require_full_address": True,
            "require_address_hash": True,
            "min_location_fields": 2,
            "location_fields": ["locality", "city_name", "district_name", "state_name", "pincode"],
            "require_pincode_or_coordinates": True,
        },
    )
    assert removed == 1
    assert len(filtered.index) == 1
    assert filtered.loc[0, "address_hash"] == "hash-a"


def test_address_builder_composes_full_address() -> None:
    frame = pd.DataFrame(
        {
            "building_name": ["TCS"],
            "road_name": ["Rajiv Gandhi Infotech Park"],
            "locality": ["Hinjewadi"],
            "city_name": ["Pune"],
            "district_name": ["Pune"],
            "state_name": ["Maharashtra"],
            "pincode": ["411057"],
        }
    )
    result = AddressBuilder().build(frame)
    assert "TCS" in result.loc[0, "full_address"]
    assert "411057" in result.loc[0, "full_address"]


def test_quality_scorer_and_statistics() -> None:
    frame = pd.DataFrame(
        {
            "building_name": ["TCS", None],
            "locality": ["Hinjewadi", "Area"],
            "city_name": ["Pune", "Pune"],
            "district_name": ["Pune", "Pune"],
            "state_name": ["Maharashtra", "Maharashtra"],
            "pincode": ["411057", "411057"],
            "quality_score": [0, 0],
        }
    )
    scored = QualityScorer().score(frame.drop(columns=["quality_score"]))
    stats = DatasetStatistics().compute(scored)
    assert scored.loc[0, "quality_score"] > scored.loc[1, "quality_score"]
    assert stats["total_rows"] == 2


def test_cleaner_removes_empty_rows_and_columns() -> None:
    frame = pd.DataFrame(
        {
            "pincode": ["500001", None, "500002"],
            "empty_col": [None, None, None],
        }
    )
    cleaner = DataCleaner()
    frame, removed_rows = cleaner.remove_empty_rows(frame)
    frame, removed_columns = cleaner.remove_empty_columns(frame)
    assert removed_rows == 1
    assert removed_columns == 1
    assert "empty_col" not in frame.columns


def test_normalizer_validates_pincode_and_coordinates() -> None:
    normalizer = AddressNormalizer()
    frame = pd.DataFrame(
        {
            "pincode": ["012345", "500001", "abc", 500001.0],
            "latitude": ["95", "17.38", "invalid"],
            "longitude": ["200", "78.48", "bad"],
        }
    )
    frame, invalid_pincodes = normalizer.validate_pincode(frame)
    frame, invalid_coords = normalizer.validate_coordinates(frame)

    assert invalid_pincodes == 2
    assert pd.isna(frame.loc[0, "pincode"])
    assert frame.loc[1, "pincode"] == "500001"
    assert frame.loc[3, "pincode"] == "500001"
    assert invalid_coords["latitude"] == 2
    assert invalid_coords["longitude"] == 2


def test_normalizer_converts_admin_codes_to_strings() -> None:
    normalizer = AddressNormalizer()
    frame = pd.DataFrame(
        {
            "pincode": [411057.0, "411058.0", None],
            "state_code": [27.0, "28", 29.0],
            "district_code": [603.0, "604.0", None],
            "local_body_type_code": [1.0, "2.0", 3.0],
            "census_2011_code": [123456.0, "123457.0", None],
        }
    )
    result = normalizer.normalize_admin_codes(
        frame,
        [
            "pincode",
            "state_code",
            "district_code",
            "local_body_type_code",
            "census_2011_code",
        ],
    )

    assert result["pincode"].dtype == "string"
    assert result.loc[0, "pincode"] == "411057"
    assert result.loc[1, "pincode"] == "411058"
    assert pd.isna(result.loc[2, "pincode"])
    assert result.loc[0, "state_code"] == "27"
    assert result.loc[1, "district_code"] == "604"
    assert result.loc[0, "local_body_type_code"] == "1"
    assert result.loc[0, "census_2011_code"] == "123456"


def test_abbreviation_expander_replaces_known_tokens() -> None:
    expander = AbbreviationExpander({"rd": "Road", "st": "Street"})
    frame = pd.DataFrame({"road_name": ["Main Rd", "Park St"]})
    result = expander.expand(frame, ["road_name"])
    assert result.loc[0, "road_name"] == "Main Road"
    assert result.loc[1, "road_name"] == "Park Street"


def test_title_case_normalization() -> None:
    assert AddressNormalizer.title_case_words("andaman and nicobar islands") == "Andaman And Nicobar Islands"


def test_address_hash_is_stable() -> None:
    normalized = normalize_for_deduplication("TCS, Hinjewadi")
    assert compute_address_hash(normalized) == compute_address_hash(normalized)


def test_preprocessing_pipeline_runs_on_sample(tmp_path: Path) -> None:
    master_dir = tmp_path / "datasets" / "master"
    processed_dir = tmp_path / "datasets" / "processed"
    reports_dir = tmp_path / "reports"
    dict_dir = tmp_path / "datasets" / "dictionaries"
    master_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)
    dict_dir.mkdir(parents=True)

    master_file = master_dir / "master_dataset.csv"
    master_file.write_text(
        "building_name,locality,city_name,district_name,state_name,pincode,latitude,longitude,source_file\n"
        "TCS,Hinjewadi,Pune,Pune,Maharashtra,411057,18.59,73.73,sample.csv\n"
        "TCS,Hinjewadi,Pune,Pune,Maharashtra,411057,18.59,73.73,sample.csv\n"
        "Bad,Bad,Bad,Bad,Bad,012345,999,bad,sample.csv\n",
        encoding="utf-8",
    )
    (dict_dir / "abbreviations.json").write_text("{}", encoding="utf-8")

    config = tmp_path / "preprocessing.yaml"
    project_config = Path(__file__).resolve().parent.parent / "configs" / "preprocessing.yaml"
    updated = project_config.read_text(encoding="utf-8")
    updated = updated.replace(
        "input_dataset: datasets/master/master_dataset.csv",
        f"input_dataset: {master_file.as_posix()}",
    )
    updated = updated.replace(
        "output_dataset: datasets/processed/final_clean_dataset.csv",
        f"output_dataset: {(processed_dir / 'final_clean_dataset.csv').as_posix()}",
    )
    updated = updated.replace(
        "output_metadata: datasets/processed/preprocessing_metadata.json",
        f"output_metadata: {(processed_dir / 'preprocessing_metadata.json').as_posix()}",
    )
    updated = updated.replace(
        "preprocessing_report: reports/preprocessing_report.json",
        f"preprocessing_report: {(reports_dir / 'preprocessing_report.json').as_posix()}",
    )
    updated = updated.replace(
        "abbreviations: datasets/dictionaries/abbreviations.json",
        f"abbreviations: {(dict_dir / 'abbreviations.json').as_posix()}",
    )
    config.write_text(updated, encoding="utf-8")

    metadata = PreprocessingPipeline(config_path=config).run()
    assert metadata["statistics"]["duplicate_rows_removed"] == 1
    assert metadata["statistics"]["duplicate_addresses_removed"] == 0
    assert metadata["statistics"]["invalid_pincodes"] == 1
    assert metadata["statistics"]["invalid_addresses_removed"] == 1
    assert (processed_dir / "final_clean_dataset.csv").exists()
    assert (reports_dir / "preprocessing_report.json").exists()

    cleaned = pd.read_csv(processed_dir / "final_clean_dataset.csv", dtype=str)
    assert len(cleaned.index) == 1
    assert "full_address" in cleaned.columns
    assert "searchable_text" in cleaned.columns
    assert "address_hash" in cleaned.columns
    assert "quality_score" in cleaned.columns
    assert cleaned["address_hash"].is_unique
    assert "Maharashtra" in cleaned.loc[0, "full_address"]
    assert "tcs" in cleaned.loc[0, "searchable_text"]
