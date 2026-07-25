# Indian Address Geocoding & Search Engine — Full Project Summary

Detailed overview of what this repository is, how it is built, what works today, and how the pieces fit together.

For a runnable command checklist, see [18_EndToEndRunGuide.md](18_EndToEndRunGuide.md).

---

## 1. What this project is

**Indian Address Geocoding and Resolution Engine** — a production-oriented system that:

1. Ingests heterogeneous Indian address CSVs (postal, LGD/admin hierarchy, buildings, cities, districts).
2. Standardizes them into one master schema.
3. Cleans, normalizes, and scores address quality.
4. Indexes records into **Elasticsearch**.
5. Accepts free-text user queries, detects entities and intent, retrieves candidates, re-ranks them, and returns a **best match** with confidence.

Typical use cases: address search, autocomplete/suggest, pincode/locality lookup, office/building lookup, nearby/reverse geocode (when lat/lon exist).

---

## 2. Goals and design principles

| Principle | How it shows up |
|-----------|-----------------|
| Modular pipeline | Separate packages: `ingestion/`, `preprocessing/`, `es_index/`, `search/`, `ranking/`, `api/` |
| Config-driven | Paths, aliases, analyzers, quality weights in `configs/*.yaml` |
| Traceability | Every row keeps `source_file`; phase metadata JSON + reports |
| CSV-first data | Raw inputs live under `datasets/raw/csv/` and are auto-discovered |
| Search-first UX | CLI and API surface a `best_match` (top-1) plus ranked candidates |

---

## 3. Technology stack

| Layer | Stack |
|-------|--------|
| Language | Python 3.10+ |
| Data | pandas, PyYAML, rapidfuzz |
| Search | Elasticsearch (local process; client via `elasticsearch` Python package) |
| API | FastAPI  |
| Ranking | Heuristic combiner + optional XGBoost (`xgboost`) |
| Logging | loguru (`logs/app.log`) |
| Tests | pytest |

Elasticsearch is expected on `http://localhost:9200` (configured in `configs/elasticsearch.yaml` / `.env`). This project is run **without Docker** in the standard workflow.

---

## 4. End-to-end architecture

```
datasets/raw/csv/*.csv
        |
        v
+-------------------+
| Ingestion         |  discover -> header detect -> load -> map columns -> merge
| ingestion/        |
+---------+---------+
          | master_dataset.csv + master_metadata.json
          v
+-------------------+
| Preprocessing     |  clean -> normalize -> build full_address -> quality -> dedupe
| preprocessing/    |
+---------+---------+
          | cleaned_dataset.csv
          v
+-------------------+
| Elasticsearch     |  create index (analyzers/mappings) -> bulk index
| es_index/         |
+---------+---------+
          | indian_addresses index
          v
+-------------------+     +----------------+
| Search pipeline   |---->| Ranking        |
| search/           |     | ranking/       |
+---------+---------+     +----------------+
          |
          +-- CLI: python -m search.search_service
          +-- API: scripts/run_api.py (FastAPI)
          +-- Orchestrator: top-1 resolve API
```

---

## 5. Repository layout

```text
Indian_Add_Geo/
├── api/                    FastAPI app (search, autocomplete, nearby, reverse)
├── app_logging/            Shared loguru setup
├── configs/
│   ├── ingestion.yaml      Schema + column aliases + paths
│   ├── preprocessing.yaml  Cleaning / full_address / quality rules
│   ├── elasticsearch.yaml  ES connection, index, search defaults
│   └── app.yaml            API metadata
├── datasets/
│   ├── raw/csv/            Input CSVs (auto-discovered)
│   ├── master/             Ingestion outputs
│   ├── processed/          Preprocessing outputs
│   ├── dictionaries/       Abbreviations, synonyms, landmarks, building keywords
│   ├── hierarchy/          Optional hierarchy reference CSVs
│   ├── ranking/            ML training JSONL (generated)
│   └── search_results/     CLI search JSON outputs (generated)
├── docs/                   Documentation (this file included)
├── es_index/               ES client, mappings, bulk indexer, ES-side queries
├── ingestion/              Phase 2 ETL
├── interfaces/             Interface stubs (future providers)
├── orchestrator/           Top-1 address resolution façade
├── parser/                 NER/parser modules (partial / transitional)
├── preprocessing/          Phase 3 cleaning & normalization
├── ranking/                Features, heuristic/ML ranker, confidence
├── reports/                Preprocess / indexing reports (generated)
├── scripts/                CLI entry points
├── search/                 Query understanding + search orchestration
├── tests/                  pytest suite
└── utils/                  Paths, YAML, strings, hashes, regex helpers
```

Stub / future folders (mostly empty scaffolding): `providers/`, parts of `interfaces/`, `hierarchy/` strategies. Real work today is in the packages listed above.

---

## 6. Data pipeline (detail)

### 6.1 Ingestion (`ingestion/`)

**Entry:** `python scripts/ingest_data.py`  
**Config:** `configs/ingestion.yaml`

| Step | Module | Behavior |
|------|--------|----------|
| Discover | `pipeline` + `file_utils` | All `.csv` under `datasets/raw/csv/` (recursive) |
| Header detect | `header_detector.py` | Score first N rows against aliases; pick best header row |
| Load | `csv_loader.py` | Encoding fallback: utf-8, utf-8-sig, latin-1, cp1252 |
| Validate | `validator.py` | Reject empty/corrupt frames |
| Map schema | `merger.py` (`SchemaStandardizer`) | Exact then fuzzy (≥88%) alias → standard column |
| Merge | `DatasetMerger` | Align to standard schema, add `source_file`, concat |

**Outputs**

- `datasets/master/master_dataset.csv`
- `datasets/master/master_metadata.json` (per-file mapping, unmapped columns, row counts)

**Important:** New CSVs need **no Python change** if headers match existing aliases. Unusual headers → add aliases under `column_aliases` in `ingestion.yaml`. Always inspect `unmapped_columns` in metadata after ingest.

Examples of aliases added for building/city dumps:

| Source header | Standard column |
|---------------|-----------------|
| `bldgname` | `building_name` |
| `bldgno` | `building_number` |
| `bldg_address` / `city_address` / `district_address` | `full_address` |
| `citycode` | `city_code` |
| `localityname` / `villagename` | `locality` |

### 6.2 Preprocessing (`preprocessing/`)

**Entry:** `python scripts/preprocess_data.py`  
**Config:** `configs/preprocessing.yaml`

Pipeline highlights:

- Drop empty rows/columns; strip invalid characters
- Unicode NFKC + invisible-char cleanup
- NULL-like string → missing; fill name from code where configured
- Abbreviation expansion (`Rd` → `Road`, etc.)
- Symbol cleanup (`sector - 21` → `sector 21`)
- Title-case / geo name standardization; pincode & lat/lon validation
- **`full_address` build** from components; **preserve** source `full_address` when already present (e.g. rich `bldg_address`)
- Address fingerprint dedupe + quality score
- Stats + `reports/preprocessing_report.json`

**Outputs**

- `datasets/processed/cleaned_dataset.csv`
- `datasets/processed/preprocessing_metadata.json`

### 6.3 Elasticsearch indexing (`es_index/`)

**Entries**

- `python scripts/create_es_index.py` / `--recreate`
- `python scripts/index_addresses.py` / `--recreate-index`
- `python scripts/index_stats.py`

**Config:** `configs/elasticsearch.yaml`

| Piece | Role |
|-------|------|
| `client.py` | Client factory, retries, ping/test connection |
| `index_manager.py` | Settings (analyzers, edge n-gram, synonyms), mappings, create/delete/stats |
| `document_mapper.py` | Row → ES document; `location` geo-point when lat/lon valid |
| `bulk_indexer.py` / `indexing_pipeline.py` | Chunked bulk load + retries + reports |

Default index name: **`indian_addresses`**.

Searchable fields include: `full_address`, `searchable_text`, `building_name`, `office_name`, `road_name`, `locality`, `city_name`, `district_name`, `state_name`, `pincode`, `quality_score`, geo `location`.

Analyzers support lowercase/asciifolding, synonym list (`datasets/dictionaries/address_synonyms.txt`), and edge n-grams for autocomplete. Synonym file changes require **index recreate** to take effect.

---

## 7. Search pipeline (detail)

### 7.1 Query understanding (`search/`)

| Module | Responsibility |
|--------|----------------|
| `query_normalizer.py` | Lowercase cleanup, abbreviations, state expansions |
| `query_parser.py` | Tokens, phrases, **intent** (locality, office, building, pincode, full address, …) |
| `entity_detector.py` | `building_name`, `office_name`, `road_name`, `locality`, `city`, `pincode`, landmark, … |
| `locality_aliases.py` | Spelling variants (`hinjewadi` ↔ `hinjavadi`, `bangalore` ↔ `bengaluru`, …) |
| `query_builder.py` | Strategy-specific ES bool queries (exact/fuzzy/phrase/autocomplete/city/locality/office/…) |
| `search_service.py` | Orchestrates analyze → plan → ES retrieve → dedupe → rerank → `best_match` |
| `search_results.py` | Dataclasses + JSON shape including `best_match` |
| `reranker.py` | Thin wrapper over `ranking.MLRanker` |

**Strategies** (auto-selected from intent/entities): `exact`, `fuzzy`, `phrase`, `autocomplete`, `city`, `locality`, `district`, `state`, `building`, `office`, `road`, `full_address`, `pincode`, hierarchical, `geospatial`, `auto`.

Entity-driven strategy resolution prefers office / full_address / locality+city when those entities are present (not only coarse intent).

### 7.2 Ranking & confidence (`ranking/`)

| Module | Responsibility |
|--------|----------------|
| `feature_engineering.py` | Query–candidate features (ratios, token overlap, exact field flags, BM25, quality, geo) |
| `similarity.py` | rapidfuzz helpers |
| `scorer.py` | Heuristic score combiner + offline metrics (nDCG, MRR, …) |
| `confidence_score.py` | Confidence 0–0.99 + label (low/medium/high/exact) |
| `ranker.py` | Optional XGBoost load; **entity-fit** ranking when entities are clear |

**Entity fit** (locality similarity with prefix + aliases, city/district match, office/building/pincode) is the primary signal when the query has usable entities. This avoids a weak ML model crowning wrong fuzzy hits (e.g. `Shindewadi` over `Hinjavadi`).

Sort order for results: **confidence → score → BM25** (highest first). `results[0]` and `best_match` agree.

### 7.3 Orchestrator

`orchestrator/address_resolution_orchestrator.py` wraps `SearchService.search` and returns:

- `best_match` — top-1 address + confidence + explanation  
- `alternatives` — next candidates  

### 7.4 CLI behavior

```powershell
python -m search.search_service --query "hinjewadi pune"
```

- Prints **BEST MATCH** by default (not the full candidate dump).
- Saves full JSON to `datasets/search_results/<timestamp>_<slug>.json` and `latest_search.json`.
- `-v` / `--verbose` → print full JSON.
- `--dry-run` → analysis + query body only (no ES).
- `--no-save` → do not write result files.

---

## 8. API (`api/`)

**Entry:** `python scripts/run_api.py` → `http://localhost:8000` (docs at `/docs`)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | App + ES connectivity + index name |
| `POST /search` | Full search pipeline; includes `best_match` + candidates |
| `GET /autocomplete` | Prefix / edge-ngram style suggestions |
| `GET /suggest` | Fuzzy suggestions |
| `GET /nearby` | Geo radius search |
| `GET /reverse-geocode` | Nearest address to a point |

Request body for search supports `query`, `strategy`, `size`, filters (`state`, `city`, `locality`, …), and `lat`/`lon`/`distance`.

---

## 9. ML ranking (optional)

Default path needs **no** trained model.

To train:

1. `python scripts/build_ranking_dataset.py --num-queries 1500`  
   → `datasets/ranking/train.jsonl` (self-supervised from cleaned data + ES retrieval)
2. `python scripts/train_ranker.py`  
   → `models/ranking_model.json` (+ feature sidecar)

The ranker auto-loads that file when present. Remove/rename the file to force heuristic + entity-fit only.

---

## 10. Configuration summary

| File | Controls |
|------|----------|
| `configs/ingestion.yaml` | Raw path, standard columns, **column_aliases**, dtypes |
| `configs/preprocessing.yaml` | Paths, `full_address_components`, quality weights, null-like, abbreviation columns |
| `configs/elasticsearch.yaml` | Hosts, index name/shards, batch size, fuzzy/phrase/autocomplete settings, ranking model path |
| `configs/app.yaml` | API title / default top_k |
| `.env` | `ELASTIC_HOST`, credentials, index override, log level |

---

## 11. Generated vs permanent artifacts

| Path | Keep / regenerate |
|------|-------------------|
| `datasets/raw/csv/` | **Keep** — source of truth |
| `datasets/dictionaries/` | **Keep** — edit as needed |
| `datasets/master/*` | Regenerated by ingestion |
| `datasets/processed/*` | Regenerated by preprocessing |
| `reports/*` | Regenerated |
| `datasets/search_results/*` | Regenerated by CLI searches |
| `datasets/ranking/train.jsonl` | Regenerated by ranking dataset builder |
| `models/ranking_model.json*` | Regenerated by trainer |
| Elasticsearch index | Recreated via `--recreate` / `--recreate-index` |

---

## 12. Testing

```powershell
python -m pytest -q
python -m pytest tests/test_search.py -q
python -m pytest tests/test_api.py -q
python -m pytest tests/test_ingestion.py -q
python -m pytest tests/test_preprocessing.py -q
python -m pytest tests/test_elasticsearch.py -q
```

Many search/API tests mock Elasticsearch so they can run without a live cluster.

---

## 13. Current capabilities vs gaps

### Working today

- Multi-source CSV ingestion with alias mapping and metadata audit  
- Full preprocessing → quality-scored cleaned dataset  
- ES index create + bulk load with address analyzers  
- Free-text search with intent/entities, multi-strategy queries  
- Best-match + confidence; CLI/API/orchestrator  
- Optional XGBoost learning-to-rank  
- Autocomplete / suggest / nearby / reverse geocode endpoints  

### Known limitations

- Coverage depends on data: village/pincode dumps are strong; commercial POIs/office names need CSVs that contain them  
- Rule-based entity detection (not a production NER model)  
- `providers/` and some `interfaces/` / hierarchy validators are still stubs  
- Synonym / mapping changes need re-ingest and/or index recreate as appropriate  
- Geo features require rows with valid latitude/longitude  

---

## 14. Recommended operating workflows

### First-time / after adding CSVs

```powershell
.\.venv\Scripts\Activate.ps1
curl http://localhost:9200

# If rebuilding data outputs — delete master/processed/reports as in End-to-End guide
python scripts/ingest_data.py
# Review master_metadata.json unmapped_columns for new files
python scripts/preprocess_data.py
python scripts/index_addresses.py --recreate-index
python scripts/index_stats.py
```

### Daily search / API

```powershell
curl http://localhost:9200
python -m search.search_service --query "hinjewadi pune"
python scripts/run_api.py
```

### After column mapping fixes

Re-run **ingest → preprocess → reindex** (aliases alone do not update an existing master/index).

---

## 15. Related documentation

| Doc | Topic |
|-----|--------|
| [01_ProjectOverview.md](01_ProjectOverview.md) | Original goals / phases |
| [02_SystemArchitecture.md](02_SystemArchitecture.md) | Early module map (ingestion/preprocess) |
| [04_DatasetDescription.md](04_DatasetDescription.md) | Raw file types & schema |
| [05_Preprocessing.md](05_Preprocessing.md) | Preprocess deep dive |
| [07_DataIngestion.md](07_DataIngestion.md) | Ingestion deep dive |
| [08_SearchStrategies.md](08_SearchStrategies.md) | Search design notes |
| [16_FutureScope.md](16_FutureScope.md) | Roadmap / remaining tasks |
| [18_EndToEndRunGuide.md](18_EndToEndRunGuide.md) | **Commands to run (no Docker)** |

---

## 16. One-paragraph summary

This repository turns mixed Indian address CSVs into a searchable Elasticsearch index and exposes a full query pipeline (normalize → entities → intent → retrieve → dedupe → confidence-ranked best match) through a CLI, FastAPI, and a thin orchestrator. Data setup is config-driven and regenerable; day-to-day use only needs a local Elasticsearch instance and the search or API entry points. Search quality scales with data richness (buildings/offices) and with ongoing alias, synonym, and ranking improvements — not with Docker or a full project rewrite.
