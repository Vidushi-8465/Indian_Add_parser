# Documentation Index

Indian Address Geocoding and Resolution Engine — technical documentation.

| # | Document | Description | Status |
|---|----------|-------------|--------|
| 01 | [Project Overview](01_ProjectOverview.md) | Goals, scope, and phases | ✅ |
| 02 | [System Architecture](02_SystemArchitecture.md) | Module layout and data flow | ✅ |
| 03 | [Data Pipeline](03_DataPipeline.md) | End-to-end ETL pipeline | ✅ |
| 04 | [Dataset Description](04_DatasetDescription.md) | Raw inputs and master schema | ✅ |
| 05 | [Preprocessing](05_Preprocessing.md) | Phase 3 cleaning and normalization | ✅ |
| 06 | [Normalization Rules](06_NormalizationRules.md) | Column mapping and text rules | ✅ |
| 07 | [Data Ingestion](07_DataIngestion.md) | Phase 2 ingestion engine | ✅ |
| 08 | [NER Parser](08_NERParser.md) | Address parsing (planned) | 🔜 |
| 09 | [Elasticsearch](09_Elasticsearch.md) | Indexing (planned) | 🔜 |
| 10 | [ML Ranking](10_MLRanking.md) | Ranking (planned) | 🔜 |
| 11 | [Hierarchy Validation](11_HierarchyValidation.md) | Admin hierarchy (planned) | 🔜 |
| 12 | [API](12_API.md) | REST API (planned) | 🔜 |
| 13 | [Testing](13_Testing.md) | Test commands and coverage | ✅ |
| 14 | [Performance Metrics](14_PerformanceMetrics.md) | Benchmarks (planned) | 🔜 |
| 15 | [Deployment](15_Deployment.md) | Docker and deployment (planned) | 🔜 |
| 16 | [Future Scope](16_FutureScope.md) | Roadmap | ✅ |

## Quick commands

```powershell
# Phase 2 – Ingestion
python scripts\ingest_data.py

# Phase 3 – Preprocessing
python scripts\preprocess_data.py

# Tests
python -m pytest tests\ -v
```
