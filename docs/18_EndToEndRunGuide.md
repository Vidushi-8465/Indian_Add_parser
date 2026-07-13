# End-to-End Run Guide

Commands to run the Indian Address Search Engine from a clean checkout through to a
running API — mapped to the phases in `docs/16_FutureScope.md`.

Run everything from the project root: `C:\Vidushi\Indian_Add_Geo`.
Commands are shown for **Windows PowerShell** (your shell).

---

## ⏱️ Do I have to re-run Phases 1 & 2 every time? — No.

The expensive work — **ingestion → preprocessing → index creation → bulk indexing
(~1.9M records)** — is **one-time setup** (Steps 1–4 below). Once the data is in
Elasticsearch it stays there. You only repeat those steps if:

- the raw CSV data changes, or
- you delete/recreate the Elasticsearch index.

**Every day / normal use = Step 0 (start ES) + Steps 6 or 7 (query / API).** Nothing else.

| Step | Cost | Repeat? |
|------|------|---------|
| 0. Start Elasticsearch | seconds | every session |
| 1. Ingestion | minutes | only if raw data changes |
| 2. Preprocessing | minutes | only if raw data changes |
| 3. Create index | seconds | only if index dropped |
| 4. Bulk index ~1.9M | **slow (one-time)** | only if data/index changes |
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

# Start Elasticsearch (every session). Easiest via Docker:
docker run -d --name es `
  -p 9200:9200 `
  -e "discovery.type=single-node" `
  -e "xpack.security.enabled=false" `
  docker.elastic.co/elasticsearch/elasticsearch:8.14.0

# Confirm it is up (should return cluster JSON)
curl http://localhost:9200
```

Credentials (if any) go in `.env` (`ELASTIC_USERNAME`, `ELASTIC_PASSWORD`); the host
is configured in `configs/elasticsearch.yaml`.

---

## ONE-TIME DATA SETUP (Steps 1–4) — skip if the index already exists

### Step 1 — Data ingestion (Phase: Data Pipeline)
Merges the raw CSVs in `datasets/raw/csv/` into `datasets/master/master_dataset.csv`.
```powershell
python scripts/ingest_data.py
```

### Step 2 — Preprocessing (Phase: Preprocessing / Normalization)
Cleans, dedupes, scores quality → `datasets/processed/cleaned_dataset.csv`.
```powershell
python scripts/preprocess_data.py
```

### Step 3 — Create the Elasticsearch index (Phase 9: index + mapping)
```powershell
python scripts/create_es_index.py            # create if missing
python scripts/create_es_index.py --recreate # drop & recreate (destroys data)
```

### Step 4 — Bulk index the addresses (Phase 2/3: retrieval backbone) — SLOW, one-time
```powershell
python scripts/index_addresses.py
python scripts/index_addresses.py --recreate-index   # recreate index then load
```

### Step 5 — Verify the index (optional)
```powershell
python scripts/index_stats.py
```

---

## PER-USE (Steps 6–7) — this is what you run normally

### Step 6 — Search from the CLI (Phases 1–5)
`--dry-run` builds the query and shows parsed entities/intent **without** Elasticsearch
— great for confirming query understanding.

```powershell
# Dry run — inspect normalization, intent, and parsed entities (no ES needed)
python -m search.search_service --query "Flat 302 Lotus Heights Baner Pune 411045" --dry-run

# Office detection  -> OFFICE_SEARCH intent + office_name entity
python -m search.search_service --query "Reliance Corporate Office Bandra Mumbai" --dry-run

# Landmark detection -> NEARBY_SEARCH intent + landmark entity
python -m search.search_service --query "near lotus temple delhi" --dry-run

# Live search (needs the index from Steps 1–4). Returns re-ranked, deduped results.
python -m search.search_service --query "Flat 302 Lotus Heights Baner Pune 411045"

# Live search with filters / geo
python -m search.search_service --query "tcs hinjewadi" --state Maharashtra --size 10
python -m search.search_service --query "cafe" --lat 18.52 --lon 73.85 --distance 2km
```

### Step 7 — Run the API (Phase 6)
```powershell
python scripts/run_api.py
# Serves on http://localhost:8000 ; interactive docs at http://localhost:8000/docs
```

Endpoints (all use the full pipeline: normalize → entities → intent → retrieve →
dedupe → re-rank):

```powershell
# Health
curl http://localhost:8000/health

# Full address search (POST)
curl -X POST http://localhost:8000/search `
  -H "Content-Type: application/json" `
  -d '{"query":"Flat 302 Lotus Heights Baner Pune 411045","strategy":"auto","size":10}'

# Autocomplete (prefix)
curl "http://localhost:8000/autocomplete?q=lotus%20heig&size=10"

# Suggest (fuzzy)
curl "http://localhost:8000/suggest?q=lotus%20hights%20baner&size=10"

# Nearby (geo radius)
curl "http://localhost:8000/nearby?lat=18.52&lon=73.85&distance=2km&size=20"

# Reverse geocode (nearest address to a point)
curl "http://localhost:8000/reverse-geocode?lat=18.52&lon=73.85"
```

---

## Phase 4 & 5 — ML Re-ranking (optional)

The re-ranker (`ranking/`) runs **out of the box using a heuristic score combiner**
(BM25 + exact-match + quality). No model file is required — search works immediately.

To use a trained XGBoost model instead, point the ranker at a model file:
```powershell
$env:RANKING_MODEL_PATH = "models/ranking_model.json"
```
If the file is absent, the system silently falls back to the heuristic. (Training a
model requires a labeled `(query, candidate, relevant)` dataset — not shipped, since
there is no ground-truth label set yet.)

---

## Phase 8 — Testing

```powershell
python -m pytest -q                    # full suite
python -m pytest tests/test_search.py -q   # search pipeline only (no ES needed)
python -m pytest tests/test_api.py -q      # API (mocks Elasticsearch)
```

---

## Phase 9 — Deployment (Docker)

Bring up Elasticsearch + API together:
```powershell
# First set configs/elasticsearch.yaml -> connection.hosts: ["http://elasticsearch:9200"]
docker compose up --build
```
Then run the one-time data setup (Steps 1–4) inside the api container the first time:
```powershell
docker compose exec api python scripts/ingest_data.py
docker compose exec api python scripts/preprocess_data.py
docker compose exec api python scripts/index_addresses.py --recreate-index
```
The API is then available at `http://localhost:8000`.

---

## Full pipeline (reference)

```
User query
  -> normalize (spelling, abbreviations, dedupe)      [search/query_normalizer.py]
  -> entity detection (building/office/landmark/...)  [search/entity_detector.py]
  -> intent detection                                 [search/query_parser.py]
  -> Elasticsearch query build (boost/filter/geo)     [search/query_builder.py]
  -> retrieve top 100 + dedupe                         [search/search_service.py]
  -> re-rank (ML or heuristic) + confidence            [ranking/]
  -> best addresses returned
```
