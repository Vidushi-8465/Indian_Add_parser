# Phase 1–3 Gap Closure — Changes & Commands

This document records the Phase 1–3 improvements made against `docs/16_FutureScope.md`
and the commands to run to verify them.

---

## What changed

### 1. Office entity detection (Phase 1.1 / 1.3)
- Added `office_name` field to `SearchEntities` (`search/search_results.py`).
- Added office-marker detection to `EntityDetector` (`search/entity_detector.py`),
  driven by `office_types` in `datasets/dictionaries/building_keywords.json`
  (with a built-in fallback list).
- Added `OFFICE_SEARCH` intent to `QueryParser` (`search/query_parser.py`).
- Added a dedicated `build_office_query` strategy + `office_name` boost clause in
  `search/query_builder.py`; registered `office` strategy in `SearchService`.

### 2. Landmark detection (Phase 1.1 / 1.3)
- Added `landmark` field to `SearchEntities`.
- Populated `datasets/dictionaries/landmarks.json` (prepositions + landmark keywords).
- Added landmark detection to `EntityDetector` (preposition-anchored, keyword-bounded).
- Added `NEARBY_SEARCH` intent to `QueryParser` (mapped to the `fuzzy` strategy, which
  applies the landmark boost clause).

### 3. Candidate deduplication (Phase 3)
- `SearchService._retrieve_candidates` now drops duplicate candidates, keyed by
  `address_hash` → normalized `full_address` → document id, keeping the highest-scoring
  (first) hit and re-numbering `retrieval_position` / `es_rank`.

### 4. Improved query normalization (Phase 1.2)
- Expanded `ABBREVIATIONS` and `SPELLING_CORRECTIONS` in `search/query_normalizer.py`
  (common Indian city/state misspellings + address abbreviations).
- Added `extract_numbers()` and `has_potential_pincode()` helpers.

### 5. Cleanup
- Deleted the orphaned, unused `preprocessing/query_normalizer.py` (its useful
  abbreviations, spelling corrections, and helpers were migrated into the live
  `search/query_normalizer.py`).

---

## Commands to run

Run these from the project root: `C:\Vidushi\Indian_Add_Geo`.

### Run the search test suite (fastest check — no Elasticsearch needed)
```bash
python -m pytest tests/test_search.py -q
```

### Run the full test suite
```bash
python -m pytest -q
```

### Dry-run the pipeline to inspect parsed entities + query body (no Elasticsearch needed)
The `--dry-run` flag builds the query without executing it, so you can confirm the
new office/landmark entities and intent detection.

```bash
# Office detection -> OFFICE_SEARCH intent, office_name entity
python -m search.search_service --query "Reliance Corporate Office Bandra Mumbai" --dry-run

# Landmark detection -> NEARBY_SEARCH intent, landmark entity
python -m search.search_service --query "near lotus temple delhi" --dry-run

# Spelling correction + abbreviation expansion
python -m search.search_service --query "appartment nr park Banglore Maharastra" --dry-run
```

Look for `analysis.intent`, `analysis.parsed_entities.office_name`,
`analysis.parsed_entities.landmark`, and `analysis.normalized_query` in the JSON output.

### Live search (requires a running Elasticsearch with the index populated)
```bash
python -m search.search_service --query "Reliance Corporate Office Bandra Mumbai"
```
Deduplication applies to the `retrieved_candidates` returned here.
