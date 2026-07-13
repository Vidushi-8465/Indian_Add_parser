# Project Overview

Indian Address Geocoding and Resolution Engine.

## Documentation

Full technical docs: **[docs/README.md](docs/README.md)**

| Phase | Doc |
|-------|-----|
| Ingestion (Phase 2) | [docs/07_DataIngestion.md](docs/07_DataIngestion.md) |
| Preprocessing (Phase 3) | [docs/05_Preprocessing.md](docs/05_Preprocessing.md) |
| Pipeline overview | [docs/03_DataPipeline.md](docs/03_DataPipeline.md) |

## Quick start

```powershell
python scripts\ingest_data.py      # Phase 2
python scripts\preprocess_data.py  # Phase 3
```

## Project structure

```text
Indian_Add_Geo/
├── .env
├── .env.example
├── .git/
├── .gitignore
├── .pytest_cache/
├── _execute_tests.bat
├── __pycache__/
├── api/
│   ├── app.py
│   ├── main.py
│   ├── middleware.py
│   ├── routes.py
│   ├── schemas.py
│   └── __pycache__/
├── app_logging/
│   ├── __init__.py
│   ├── logger.py
│   └── __pycache__/
├── configs/
│   ├── app.yaml
│   ├── elasticsearch.yaml
│   ├── ingestion.yaml
│   ├── logging.yaml
│   ├── parser.yaml
│   ├── preprocessing.yaml
│   └── ranking.yaml
├── conftest.py
├── datasets/
│   ├── dictionaries/
│   ├── hierarchy/
│   ├── master/
│   ├── processed/
│   └── raw/
├── docs/
│   ├── 01_ProjectOverview.md
│   ├── 02_SystemArchitecture.md
│   ├── 03_DataPipeline.md
│   ├── 04_DatasetDescription.md
│   ├── 05_Preprocessing.md
│   ├── 06_NormalizationRules.md
│   ├── 07_DataIngestion.md
│   ├── 07_NERParser.md
│   ├── 08_SearchStrategies.md
│   ├── 09_Elasticsearch.md
│   ├── 10_MLRanking.md
│   ├── 11_HierarchyValidation.md
│   ├── 12_API.md
│   ├── 13_Testing.md
│   ├── 14_PerformanceMetrics.md
│   ├── 15_Deployment.md
│   ├── 16_FutureScope.md
│   ├── README.md
│   └── images/
├── elasticsearch/
│   ├── bulk_index.py
│   ├── connection.py
│   ├── fuzzy_search.py
│   ├── indexer.py
│   ├── mappings.py
│   └── search.py
├── es_index/
│   ├── bulk_indexer.py
│   ├── client.py
│   ├── document_mapper.py
│   ├── indexing_logger.py
│   ├── indexing_pipeline.py
│   ├── indexing_report.py
│   ├── index_manager.py
│   ├── query_builder.py
│   ├── search_logger.py
│   ├── search_service.py
│   └── __pycache__/
├── hierarchy/
│   ├── building_strategy.py
│   ├── pincode_strategy.py
│   ├── planner.py
│   ├── state_city_strategy.py
│   ├── strategies.py
│   └── validator.py
├── ingestion/
│   ├── csv_loader.py
│   ├── header_detector.py
│   ├── merger.py
│   ├── pipeline.py
│   ├── validator.py
│   └── __pycache__/
├── interfaces/
│   ├── normalization_interface.py
│   ├── parser_interface.py
│   ├── provider_interface.py
│   ├── ranking_interface.py
│   └── search_interface.py
├── logging/
│   ├── formatter.py
│   ├── request_context.py
│   └── __pycache__/
├── logs/
├── metrics/
│   ├── counters.py
│   ├── latency.py
│   └── profiler.py
├── models/
│   ├── address.py
│   ├── candidate.py
│   ├── ner_token.py
│   ├── parsed_address.py
│   ├── response.py
│   └── search_result.py
├── orchestrator/
│   └── address_resolution_orchestrator.py
├── parser/
│   ├── __init__.py
│   ├── confidence.py
│   ├── entity_mapper.py
│   ├── ner_model.py
│   ├── parser_pipeline.py
│   ├── postprocessor.py
│   └── tokenizer.py
├── preprocessing/
│   ├── abbreviation_expander.py
│   ├── address_builder.py
│   ├── address_deduplicator.py
│   ├── cleaner.py
│   ├── deduplicator.py
│   ├── normalizer.py
│   ├── null_handler.py
│   ├── preprocessing_pipeline.py
│   ├── quality_scorer.py
│   ├── report_generator.py
│   ├── statistics.py
│   ├── symbol_normalizer.py
│   ├── unicode_normalizer.py
│   └── __pycache__/
├── providers/
│   ├── dictionary_provider.py
│   ├── elastic_provider.py
│   ├── hierarchy_provider.py
│   └── ner_provider.py
├── pyproject.toml
├── ranking/
│   ├── __init__.py
│   ├── confidence_score.py
│   ├── feature_engineering.py
│   ├── ranker.py
│   ├── scorer.py
│   └── __pycache__/
├── README.md
├── reports/
│   ├── .gitkeep
│   ├── indexing_performance_report.json
│   ├── indexing_report.json
│   └── preprocessing_report.json
├── requirements-ingestion.txt
├── requirements.txt
├── scripts/
│   ├── bulk_index.py
│   ├── create_es_index.py
│   ├── create_index.py
│   ├── index_addresses.py
│   ├── index_stats.py
│   ├── ingest_data.py
│   ├── preprocess_data.py
│   ├── run_api.py
│   ├── run_engine.py
│   └── train_parser.py
├── search/
│   ├── __init__.py
│   ├── entity_detector.py
│   ├── query_builder.py
│   ├── query_normalizer.py
│   ├── query_parser.py
│   ├── reranker.py
│   ├── search_results.py
│   ├── search_service.py
│   └── __pycache__/
├── tests/
│   ├── test_api.py
│   ├── test_csv_preview.py
│   ├── test_elasticsearch.py
│   ├── test_hierarchy.py
│   ├── test_ingestion.py
│   ├── test_parser.py
│   ├── test_preprocessing.py
│   ├── test_search.py
│   └── __pycache__/
├── utils/
│   ├── constants.py
│   ├── file_utils.py
│   ├── hash_utils.py
│   ├── helpers.py
│   ├── regex_utils.py
│   ├── string_utils.py
│   └── __pycache__/
├── venv/
└── reports/
```

# Indian Address Search Engine - Project Summary

## Project Goal
Build an intelligent address search engine for Indian addresses using:

- Elasticsearch
- NLP-based Query Understanding
- Entity Detection
- Candidate Retrieval
- ML Re-ranking
- Confidence Scoring

Pipeline:

```
User Query
    ↓
Query Normalization
    ↓
Entity Detection (NER)
    ↓
Intent Detection
    ↓
Query Builder
    ↓
Elasticsearch Retrieval (Top 100)
    ↓
ML Re-ranking
    ↓
Confidence Scoring
    ↓
Final Results
```

---

# ✅ Completed

## 1. Data Processing

- Combined datasets
- Cleaned dataset
- Generated cleaned CSV (~1.9M addresses)

---

## 2. Elasticsearch

Completed:

- Installed Elasticsearch
- Created `indian_addresses` index
- Custom analyzers
- Synonyms
- Edge NGram
- Geo Point mapping
- Indexed

```
1,917,228 documents
```

---

## 3. Search Pipeline

Implemented

- Query Normalization
- Entity Detection
- Intent Detection
- Search Strategy Selection
- Query Builder
- Elasticsearch Search

---

## 4. Entity Detection

Can detect:

- Building Name
- Flat Number
- Locality
- Road Name
- City
- State
- District
- Pincode
- Office Name

---

## 5. Intent Detection

Supports

- FULL_ADDRESS_SEARCH
- PINCODE_SEARCH
- CITY_SEARCH
- LOCALITY_SEARCH
- ROAD_SEARCH
- BUILDING_SEARCH
- OFFICE_SEARCH

---

## 6. Candidate Retrieval

Implemented

- Elasticsearch retrieves Top 100 candidates
- Candidate pool returned separately
- Final results separated from retrieved candidates

---

## 7. Search Output

Returns

- Retrieved candidates
- Final results
- Score
- Confidence
- ES Rank
- Retrieval Position
- Execution Time

---

# ⚠ Current Issues

## Locality Search

Example

```
Baner Pune
```

Returns

```
0 results
```

Needs Query Builder improvement.

---

## Road Search

Example

```
MG Road Pune
```

Only city-level result returned.

Needs proper road matching.

---

## Building Search

Building names are not strongly boosted.

---

## Office Search

Office names are not prioritised.

---

## Phrase Search

Needs stronger `match_phrase` queries.

---

## Fuzzy Search

Current fuzzy search is weak.

Typos are not handled well.

---

## Autocomplete

Needs

- prefix search
- bool_prefix
- search_as_you_type
- completion suggester

---

## Query Builder

Needs better boosting hierarchy

Priority should be

```
Building
>
Office
>
Road
>
Locality
>
City
>
State
```

---

# ❌ Remaining Work

## Query Builder

Improve

- locality search
- road search
- office search
- building search
- phrase search
- fuzzy search
- autocomplete
- boosting

---

## ML Re-ranking

Still not implemented.

Need:

- Feature Engineering
- Ranking Dataset
- XGBoost / LightGBM
- Ranking Model
- Model Inference
- Score Combination

---

## Confidence Scoring

Generate confidence using

- BM25 Score
- ML Score
- Address Completeness
- Exact Match
- Entity Match %
- Geo Distance

---

## Evaluation

Create metrics

- Precision@10
- Recall@10
- MRR
- NDCG
- Search Accuracy
- Latency

---

## Testing

Need tests for

- Entity Detector
- Intent Detector
- Query Builder
- Retrieval
- ML Ranking
- Confidence Score

---

## API

Build

- FastAPI
- REST endpoints
- Swagger

Example

```
POST /search
```

---

## UI (Optional)

Simple frontend

- Search box
- Suggestions
- Top Results
- Confidence
- Location on Map

---

# Final Roadmap

```
✅ Dataset Cleaning
        ↓
✅ Elasticsearch Indexing
        ↓
✅ Query Understanding
        ↓
✅ Entity Detection
        ↓
✅ Intent Detection
        ↓
✅ Candidate Retrieval (Top 100)
        ↓
⬜ Improve Query Builder
        ↓
⬜ Better Fuzzy Search
        ↓
⬜ Better Phrase Search
        ↓
⬜ Better Autocomplete
        ↓
⬜ ML Re-ranking
        ↓
⬜ Confidence Scoring
        ↓
⬜ Evaluation
        ↓
⬜ FastAPI
        ↓
⬜ UI
```

# Current Progress

| Module | Status |
|----------|--------|
| Dataset Cleaning | ✅ Complete |
| Elasticsearch Index | ✅ Complete |
| Indexing | ✅ Complete |
| Query Normalization | ✅ Complete |
| Entity Detection | ✅ Complete |
| Intent Detection | ✅ Complete |
| Candidate Retrieval | ✅ Complete |
| Query Builder | 🟡 Needs Improvement |
| Locality Search | ❌ Pending |
| Road Search | ❌ Pending |
| Building Search | ❌ Pending |
| Office Search | ❌ Pending |
| Phrase Search | ❌ Pending |
| Fuzzy Search | ❌ Pending |
| Autocomplete | ❌ Pending |
| ML Re-ranking | ❌ Pending |
| Confidence Scoring | ❌ Pending |
| Evaluation | ❌ Pending |
| FastAPI | ❌ Pending |
| UI | ❌ Optional |