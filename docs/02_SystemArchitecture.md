# System Architecture

## High-level flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Raw CSV files  │────▶│  Ingestion (P2)  │────▶│  master_dataset.csv │
│  datasets/raw/  │     │  ingestion/      │     │  master_metadata.json│
└─────────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                              │
                                                              ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Reports        │◀────│ Preprocessing(P3)│◀────│  cleaned_dataset.csv│
│  reports/       │     │  preprocessing/  │     │  preprocessing_meta │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
```

## Phase 2 — Ingestion modules

| Module | File | Responsibility |
|--------|------|----------------|
| Header detection | `ingestion/header_detector.py` | Score first 20 rows using YAML aliases; pick header row |
| CSV loader | `ingestion/csv_loader.py` | Read CSV with encoding fallback; log rows loaded |
| Validator | `ingestion/validator.py` | Reject empty/corrupt datasets |
| Schema standardizer | `ingestion/merger.py` | Map columns via exact + fuzzy alias matching |
| Dataset merger | `ingestion/merger.py` | Concat all files into master schema |
| Pipeline | `ingestion/pipeline.py` | Orchestrate discovery → load → validate → merge |

## Phase 3 — Preprocessing modules

| Module | File | Responsibility |
|--------|------|----------------|
| Deduplicator | `preprocessing/deduplicator.py` | Exact row deduplication |
| Data cleaner | `preprocessing/cleaner.py` | Empty rows/columns, invalid chars |
| Unicode normalizer | `preprocessing/unicode_normalizer.py` | NFKC + invisible unicode |
| Null handler | `preprocessing/null_handler.py` | NULL-like → `pd.NA`; code→name fill |
| Abbreviation expander | `preprocessing/abbreviation_expander.py` | Expand Rd, St, Nagar, etc. |
| Symbol normalizer | `preprocessing/symbol_normalizer.py` | `sector - 21` → `sector 21` |
| Address normalizer | `preprocessing/normalizer.py` | Title case, geo names, pincode/lat/long |
| Address builder | `preprocessing/address_builder.py` | Compose `full_address` |
| Address deduplicator | `preprocessing/address_deduplicator.py` | Fingerprint duplicate addresses |
| Quality scorer | `preprocessing/quality_scorer.py` | Per-row `quality_score` |
| Statistics | `preprocessing/statistics.py` | Dataset-level stats |
| Report generator | `preprocessing/report_generator.py` | `reports/preprocessing_report.json` |
| Pipeline | `preprocessing/preprocessing_pipeline.py` | End-to-end orchestrator |

## Shared utilities

| Utility | Purpose |
|---------|---------|
| `utils/string_utils.py` | Column name normalization; subdistrict detection; dedup keys |
| `utils/regex_utils.py` | Pincode pattern, invisible unicode, dash cleanup |
| `utils/hash_utils.py` | SHA-256 address hashing |
| `utils/file_utils.py` | YAML loading, path resolution, file discovery |
| `app_logging/logger.py` | Loguru console + file logging |

## Configuration files

| File | Phase |
|------|-------|
| `configs/ingestion.yaml` | Column aliases, standard schema, paths |
| `configs/preprocessing.yaml` | Cleaning rules, validation, quality weights |

## Logging

Logs are written to `logs/app.log` and stderr. Header detection, CSV loading, coordinate validation, and preprocessing warnings are logged with module tags.
