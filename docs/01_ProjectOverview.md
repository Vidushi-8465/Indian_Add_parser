# Project Overview

## Purpose

This project is an **Indian Address Geocoding and Resolution Engine**. It ingests heterogeneous government and postal address datasets, standardizes them into a single schema, cleans and normalizes the data, and (in later phases) parses, indexes, validates hierarchy, and ranks address matches.

## Design principles

- **Modular ETL pipeline** — each phase has a single responsibility
- **Config-driven** — column aliases, paths, and rules live in YAML under `configs/`
- **Traceability** — every row keeps `source_file`; metadata JSON is written per phase
- **CSV-only ingestion** — all raw files are placed in `datasets/raw/csv/`

## Pipeline phases

| Phase | Name | Input | Output | Status |
|-------|------|-------|--------|--------|
| 2 | Data Ingestion | 14 raw CSV files | `master_dataset.csv` | ✅ Done |
| 3 | Preprocessing | Master dataset | `cleaned_dataset.csv` | ✅ Done |
| 4 | Normalization | Cleaned dataset | `normalized_dataset.csv` | 🔜 Planned |
| 5 | NER Parsing | Normalized dataset | `parsed_dataset.csv` | 🔜 Planned |
| 6+ | Search, ES, Ranking, API | Parsed data | Resolution engine | 🔜 Planned |

## Repository layout

```
configs/          YAML configuration (ingestion, preprocessing, …)
ingestion/        Phase 2 – discover, load, validate, merge
preprocessing/    Phase 3 – clean, normalize, validate, dedupe
datasets/
  raw/csv/        Raw input files
  master/         Ingestion output
  processed/      Preprocessing output
  dictionaries/   Abbreviations, stopwords, etc.
reports/          Preprocessing and pipeline reports
scripts/          CLI entry points
tests/            Unit and integration tests
```

## Technology stack

- Python 3.10+
- pandas, pyyaml, loguru, rapidfuzz
- pytest for testing
