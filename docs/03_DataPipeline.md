# Data Pipeline

## Overview

The pipeline follows classic **Extract → Transform → Load** stages split into independent, rerunnable phases.

## Phase 2 — Data Ingestion

### Objective

Collect all raw address CSV files, validate them, map heterogeneous column names to a **standard schema**, and merge into one **master dataset**. No cleaning, deduplication, or ML is performed in this phase.

### Steps

1. **Discover** all `.csv` files under `datasets/raw/csv/`
2. **Load** each file with automatic header detection (`HeaderDetector`)
3. **Validate** — non-empty, has columns, no all-unnamed headers
4. **Standardize schema** — map aliases (exact then fuzzy) to standard columns
5. **Merge** all standardized frames with `pd.concat`
6. **Write** `datasets/master/master_dataset.csv` and `master_metadata.json`

### Run

```powershell
python scripts\ingest_data.py
python scripts\ingest_data.py --config configs\ingestion.yaml
```

### Outputs

| File | Description |
|------|-------------|
| `datasets/master/master_dataset.csv` | Unified master dataset (~4.5M rows from 14 files) |
| `datasets/master/master_metadata.json` | Per-file stats, column mappings, errors, warnings |

### Key design decisions

- **Subdistrict ≠ District** — `subdistrict_code` / `subdistrict_name` are separate columns; fuzzy matching blocks subdistrict columns from mapping to district fields
- **Header detection** — uses alias match scores from `ingestion.yaml`, not hardcoded row numbers
- **Source traceability** — every row includes `source_file`

---

## Phase 3 — Preprocessing

### Objective

Clean, normalize, validate, deduplicate, and enrich the master dataset into a reliable foundation for parsing and search.

### Steps

1. Remove exact duplicate rows
2. Remove empty rows and empty columns
3. Clean invalid characters (extra commas, spaces, invisible unicode)
4. Normalize null-like values to `pd.NA`
5. Fill missing names from code lookups (state_code → state_name, etc.)
6. Expand abbreviations (Rd → Road, Nagar, etc.)
7. Normalize symbols (`sector - 21` → `sector 21`)
8. Title-case and standardize geographic names
9. Validate pincode (`^[1-9][0-9]{5}$`), latitude (−90 to 90), longitude (−180 to 180)
10. Build `full_address` and `address_hash`
11. Remove duplicate addresses (e.g. `TCS Hinjewadi` vs `TCS, Hinjewadi`)
12. Compute `quality_score` per row
13. Generate statistics and report

### Run

```powershell
python scripts\preprocess_data.py
python scripts\preprocess_data.py --config configs\preprocessing.yaml
```

### Outputs

| File | Description |
|------|-------------|
| `datasets/processed/cleaned_dataset.csv` | Cleaned dataset with `full_address`, `address_hash`, `quality_score` |
| `datasets/processed/preprocessing_metadata.json` | Pipeline statistics |
| `reports/preprocessing_report.json` | Full report with dataset statistics |

---

## Phase flow diagram

```
Raw CSV (14 files)
       │
       ▼
┌──────────────┐
│  INGESTION   │
└──────┬───────┘
       ▼
master_dataset.csv
       │
       ▼
┌──────────────┐
│ PREPROCESSING│
└──────┬───────┘
       ▼
cleaned_dataset.csv
       │
       ▼ (planned)
┌──────────────┐
│ NORMALIZATION│
│  NER PARSER  │
│ ELASTICSEARCH│
└──────────────┘
```

## Metadata chain

Each phase writes JSON metadata so you can audit the pipeline:

```
master_metadata.json          ← ingestion stats per file
preprocessing_metadata.json   ← cleaning stats + dataset statistics
preprocessing_report.json     ← human-readable combined report
```
