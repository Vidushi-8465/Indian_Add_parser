# Testing

## Setup

```powershell
cd c:\Vidushi\Indian_Add_Geo
.\venv\Scripts\Activate.ps1
pip install -r requirements-ingestion.txt
```

## Run all tests

```powershell
python -m pytest tests\ -v
```

## Run by phase

```powershell
# Phase 2 – Ingestion
python -m pytest tests\test_ingestion.py -v

# Phase 3 – Preprocessing
python -m pytest tests\test_preprocessing.py -v

# CSV preview utility
python tests\test_csv_preview.py
```

## Test coverage

### Ingestion (`tests/test_ingestion.py`)

| Test | Validates |
|------|-----------|
| `test_normalize_column_name_variants` | Column name normalization |
| `test_schema_standardizer_maps_aliases` | PIN Code → pincode mapping |
| `test_subdistrict_columns_do_not_map_to_district` | Subdistrict ≠ district |
| `test_is_subdistrict_column_marker` | Sub-district detection |
| `test_header_detector_selects_alias_row` | Header row scoring |
| `test_header_detector_skips_blank_rows` | Blank row handling |
| `test_ingestion_pipeline_builds_master_dataset` | End-to-end ingestion |

### Preprocessing (`tests/test_preprocessing.py`)

| Test | Validates |
|------|-----------|
| `test_null_handler_converts_null_like_values` | NULL → pd.NA |
| `test_deduplicator_removes_duplicate_rows` | Row deduplication |
| `test_address_deduplicator_treats_punctuation_variants_as_one` | TCS Hinjewadi = TCS, Hinjewadi |
| `test_symbol_normalizer_cleans_sector_dash_pattern` | sector - 21 → sector 21 |
| `test_address_builder_composes_full_address` | full_address building |
| `test_quality_scorer_and_statistics` | quality_score + stats |
| `test_normalizer_validates_pincode_and_coordinates` | Pincode and lat/long rules |
| `test_abbreviation_expander_replaces_known_tokens` | Rd → Road |
| `test_preprocessing_pipeline_runs_on_sample` | End-to-end preprocessing |

## Manual smoke tests

```powershell
# Preview raw CSV files
python tests\test_csv_preview.py

# Full ingestion (long running ~20 min for 4.5M rows)
python scripts\ingest_data.py

# Full preprocessing
python scripts\preprocess_data.py
```

## Expected outputs after successful runs

```
datasets/master/master_dataset.csv
datasets/master/master_metadata.json
datasets/processed/cleaned_dataset.csv
datasets/processed/preprocessing_metadata.json
reports/preprocessing_report.json
logs/app.log
```
