# Data Ingestion (Phase 2)

## Objective

Build a **Data Ingestion Engine** that:

1. Discovers all raw CSV files automatically
2. Detects header rows (even with title/blank leading rows)
3. Validates files are not empty or corrupt
4. Maps heterogeneous column names to a **standard schema**
5. Merges all datasets into one **master dataset**
6. Writes metadata for monitoring and debugging

No cleaning, deduplication, or ML is performed in this phase.

## Configuration

`configs/ingestion.yaml`

| Section | Purpose |
|---------|---------|
| `paths` | Raw data dir, master output paths |
| `discovery` | CSV extensions, recursive scan |
| `reading` | Encodings, header scan row count (20) |
| `standard_columns` | Canonical schema (50+ columns) |
| `column_aliases` | Source name → standard column mappings |
| `dtype_rules` | String vs float columns |

## Header detection

**Module:** `ingestion/header_detector.py`

1. Read first 20 rows without assuming a header
2. Score each row by counting alias matches from `column_aliases`
3. Select row with highest score
4. Log detected header row for every file

Example log:

```
Detected header row 1 (1-based: 2) for 'Cities_Towns_District_State_India.csv'
| score=5.5 | matched_aliases=['sl no', 'city town', 'state code', ...]
```

## CSV loading

**Module:** `ingestion/csv_loader.py`

- Tries encodings: `utf-8`, `utf-8-sig`, `latin-1`, `cp1252`
- Uses detected header row
- Logs rows loaded and encoding used

## Schema standardization

**Module:** `ingestion/merger.py` → `SchemaStandardizer`

| Priority | Method | Confidence |
|----------|--------|------------|
| 1 | Exact alias match | 100% |
| 2 | Fuzzy alias match (≥88%) | fuzzy score |

Unmapped columns are logged in metadata but not included in master schema.

## Merge

**Module:** `ingestion/merger.py` → `DatasetMerger`

- Aligns all frames to `standard_columns`
- Concatenates with `pd.concat`
- Adds `source_file` column per row

## Run

```powershell
python scripts\ingest_data.py
python scripts\ingest_data.py --config configs\ingestion.yaml
```

## Outputs

| File | Contents |
|------|----------|
| `datasets/master/master_dataset.csv` | Unified dataset |
| `datasets/master/master_metadata.json` | Per-file mapping, rows, errors, warnings |

## Metadata example (per file)

```json
{
  "filename": "Pincodeto_Village_Mapping_2026-06-14_14-18-52.csv",
  "rows": 672196,
  "columns_mapped": 10,
  "column_mapping": {
    "SubDistrict Code": "subdistrict_code",
    "SubDistrict Name": "subdistrict_name",
    "District Code": "district_code",
    "Pincode": "pincode"
  },
  "header_row": 1,
  "encoding": "latin-1"
}
```

## Module reference

```
ingestion/
├── header_detector.py   # Alias-based header row detection
├── csv_loader.py        # CSV read + encoding fallback
├── validator.py         # Empty/corrupt validation
├── merger.py            # SchemaStandardizer + DatasetMerger
└── pipeline.py          # IngestionPipeline orchestrator

scripts/ingest_data.py   # CLI entry point
```

## Adding new datasets

1. Place CSV in `datasets/raw/csv/`
2. Add column aliases to `configs/ingestion.yaml` if needed
3. Re-run `python scripts\ingest_data.py`

New files are picked up automatically — no code changes required.
