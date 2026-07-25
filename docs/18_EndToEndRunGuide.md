# End-to-End Run Guide

Commands to run the Indian Address Search Engine from a clean checkout through to a
running API — mapped to the phases in `docs/16_FutureScope.md`.

Run everything from the project root: `C:\Vidushi\Indian_Add_Geo`.
Commands are shown for **Windows PowerShell** (your shell).

This guide assumes **Elasticsearch is installed and running locally** (not Docker).

---

## Do I have to re-run data setup every time? — No.

The expensive work — **ingestion → preprocessing → index creation → bulk indexing** —
is **one-time setup** (Steps 1–4 below). Once the data is in Elasticsearch it stays
there. You only repeat those steps if:

- raw CSVs under `datasets/raw/csv/` change (add/remove/update files), or
- you delete/recreate the Elasticsearch index.

**Normal use = Step 0 (confirm ES) + Steps 6 or 7 (CLI search / API).**

| Step | Cost | Repeat? |
|------|------|---------|
| 0. Confirm Elasticsearch | seconds | every session |
| 1. Ingestion | minutes–long | only if raw data changes |
| 2. Preprocessing | minutes–long | only if raw data changes |
| 3. Create index | seconds | only if index dropped |
| 4. Bulk index | **slow** | only if data/index changes |
| 5. Verify index | seconds | optional |
| 6. CLI search | instant | per query |
| 7. API | instant | per session |

---

## Step 0 — Prerequisites (once per machine / session)

```powershell
# Create & activate a virtual environment (once per machine)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies (once, or after requirements change)
pip install -r requirements.txt

# Copy env template if you do not have a .env yet
copy .env.example .env

# Confirm Elasticsearch is up on localhost:9200 (should return cluster JSON)
curl http://localhost:9200
```

Host and credentials are configured in `configs/elasticsearch.yaml` and can be
overridden via `.env` (`ELASTIC_HOST`, `ELASTIC_USERNAME`, `ELASTIC_PASSWORD`,
`ELASTIC_INDEX`).

---

## When you add new CSV files

1. Put new files in `datasets/raw/csv/` (ingestion auto-discovers all `.csv` files).
2. If headers are unusual, add aliases in `configs/ingestion.yaml` → `column_aliases`
   (no Python changes needed for normal column names).
3. Delete previous generated outputs, then re-run Steps 1–4.

```powershell
# Generated outputs to clear before a full rebuild
Remove-Item datasets\master\master_dataset.csv -ErrorAction SilentlyContinue
Remove-Item datasets\master\master_metadata.json -ErrorAction SilentlyContinue
Remove-Item datasets\processed\cleaned_dataset.csv -ErrorAction SilentlyContinue
Remove-Item datasets\processed\preprocessing_metadata.json -ErrorAction SilentlyContinue
Remove-Item reports\preprocessing_report.json -ErrorAction SilentlyContinue
Remove-Item reports\indexing_report.json -ErrorAction SilentlyContinue
Remove-Item reports\indexing_performance_report.json -ErrorAction SilentlyContinue
```

**Do not delete:** `datasets/raw/csv/`, `datasets/dictionaries/`, `datasets/hierarchy/`,
configs, or code.

After ingest, open `datasets/master/master_metadata.json` and check each new file’s
`unmapped_columns`. Important fields (building name/address, city address, etc.)
should appear under `column_mapping`, not unmapped.

Optional (only if you will rebuild the ML ranker after the new index is ready):

```powershell
Remove-Item datasets\ranking\train.jsonl -ErrorAction SilentlyContinue
Remove-Item models\ranking_model.json -ErrorAction SilentlyContinue
Remove-Item models\ranking_model.json.features.json -ErrorAction SilentlyContinue
```

---

## ONE-TIME DATA SETUP (Steps 1–4) — skip if the index is already current

### Step 1 — Data ingestion
Merges all CSVs in `datasets/raw/csv/` into `datasets/master/master_dataset.csv`.

```powershell
python scripts/ingest_data.py
```

### Step 2 — Preprocessing
Cleans, dedupes, builds `full_address`, scores quality →
`datasets/processed/cleaned_dataset.csv`.

```powershell
python scripts/preprocess_data.py
```

### Step 3 — Create the Elasticsearch index
```powershell
python scripts/create_es_index.py            # create if missing
python scripts/create_es_index.py --recreate # drop & recreate (destroys data)
```

### Step 4 — Bulk index addresses — SLOW
```powershell
python scripts/index_addresses.py
# Or recreate index and load in one go:
python scripts/index_addresses.py --recreate-index
```

### Step 5 — Verify the index (optional)
```powershell
python scripts/index_stats.py
```

---

## PER-USE (Steps 6–7) — what you run normally

### Step 6 — Search from the CLI

By default the CLI prints the **BEST MATCH** only and saves full JSON under
`datasets/search_results/`. Use `-v` / `--verbose` for the full candidate dump.
Use `--dry-run` to inspect normalization, intent, and entities without Elasticsearch.

```powershell
# Dry run — no ES needed
python -m search.search_service --query "Flat 302 Lotus Heights Baner Pune 411045" --dry-run

# Live search — shows BEST MATCH + writes datasets/search_results/*.json
python -m search.search_service --query "hinjewadi pune"
python -m search.search_service --query "tvs credit service" -v

# Filters / geo
python -m search.search_service --query "tcs hinjewadi" --state Maharashtra --size 10
python -m search.search_service --query "cafe" --lat 18.52 --lon 73.85 --distance 2km

# Skip saving JSON
python -m search.search_service --query "hinjewadi pune" --no-save
```

**Top-1 best address:** live search ends with a `BEST MATCH` block (address +
confidence + why). JSON includes `best_match`. For a programmatic single-answer path:

```python
from orchestrator.address_resolution_orchestrator import AddressResolutionOrchestrator
from es_index.client import build_elasticsearch_client
from utils.file_utils import load_yaml_config
from utils.constants import DEFAULT_ELASTICSEARCH_CONFIG

config = load_yaml_config(DEFAULT_ELASTICSEARCH_CONFIG)
orch = AddressResolutionOrchestrator(build_elasticsearch_client(config), config)
answer = orch.resolve("hinjewadi pune")
print(answer["best_match"])       # top-1 address + confidence + explanation
print(answer["alternatives"])     # next best candidates
```

### Step 7 — Run the API
```powershell
python scripts/run_api.py
# Serves on http://localhost:8000 ; interactive docs at http://localhost:8000/docs
```

```powershell
# Health
curl http://localhost:8000/health

# Full address search (POST)
curl -X POST http://localhost:8000/search `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"Flat 302 Lotus Heights Baner Pune 411045\",\"strategy\":\"auto\",\"size\":10}"

# Autocomplete (prefix)
curl "http://localhost:8000/autocomplete?q=lotus%20heig&size=10"

# Suggest (fuzzy)
curl "http://localhost:8000/suggest?q=lotus%20hights%20baner&size=10"

# Nearby (geo radius)
curl "http://localhost:8000/nearby?lat=18.52&lon=73.85&distance=2km&size=20"

# Reverse geocode
curl "http://localhost:8000/reverse-geocode?lat=18.52&lon=73.85"
```

---

## Phase 4 & 5 — ML Re-ranking (optional)

The re-ranker works out of the box with a **heuristic** (entity fit + BM25 +
exact-match + quality). When clear query entities are present, entity fit is
preferred over a weak trained model so locality/office matches are not demoted.

To train an XGBoost model (requires ES + populated index):

```powershell
# M1 — build training rows
python scripts/build_ranking_dataset.py --num-queries 1500
# Output: datasets/ranking/train.jsonl

# M2 — train + evaluate
python scripts/train_ranker.py
# Saves models/ranking_model.json (+ .features.json sidecar)
```

Delete or move `models/ranking_model.json` to force the heuristic-only path.
Optional config:

```yaml
# configs/elasticsearch.yaml
ranking:
  model_path: models/ranking_model.json
```

---

## Phase 8 — Testing

```powershell
python -m pytest -q
python -m pytest tests/test_search.py -q
python -m pytest tests/test_api.py -q
```

---

## Full pipeline (reference)

```
User query
  -> normalize (spelling, abbreviations, dedupe)      [search/query_normalizer.py]
  -> entity detection (building/office/landmark/...)  [search/entity_detector.py]
  -> intent detection                                 [search/query_parser.py]
  -> Elasticsearch query build (boost/filter/geo)     [search/query_builder.py]
  -> retrieve top N + dedupe                          [search/search_service.py]
  -> re-rank (entity fit / ML / heuristic) + confidence [ranking/]
  -> BEST MATCH + candidates returned / saved
```
