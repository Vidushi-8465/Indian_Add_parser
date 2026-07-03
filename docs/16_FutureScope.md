# Future Scope

## Completed

- [x] Project structure and configuration
- [x] Phase 2 — CSV ingestion with header detection and schema standardization
- [x] Expanded administrative schema (subdistrict, panchayat, local body, census codes)
- [x] Subdistrict vs district mapping protection
- [x] Phase 3 — Preprocessing (clean, validate, dedupe, full_address, hash, quality score)
- [x] Preprocessing report generation
- [x] Unit and integration tests for ingestion and preprocessing

## Planned — Phase 4: Normalization

- [ ] Advanced text normalization pipeline (`normalized_dataset.csv`)
- [ ] Phonetic matching for Indian place names
- [ ] Stopword removal from address components
- [ ] Hierarchy validation against official admin boundaries

## Planned — Phase 5: NER Parser

- [ ] Train/load NER model for Indian address entity extraction
- [ ] Tokenizer, entity mapper, confidence scoring
- [ ] Output `parsed_dataset.csv` with structured entities

## Planned — Phase 6: Elasticsearch

- [ ] Index design and bulk indexing
- [ ] Fuzzy and multi-field search strategies
- [ ] Query builder for address resolution

## Planned — Phase 7: ML Ranking

- [ ] Feature engineering for candidate addresses
- [ ] XGBoost / similarity-based ranker
- [ ] Confidence score for top match

## Planned — Phase 8: API and orchestration

- [ ] FastAPI REST endpoints
- [ ] Address resolution orchestrator
- [ ] Request logging and metrics

## Planned — Infrastructure

- [ ] Populate hierarchy CSV reference files
- [ ] Expand abbreviation and landmark dictionaries
- [ ] Performance benchmarks on 4.5M+ row dataset
- [ ] Docker Compose deployment with Elasticsearch + Kibana
- [ ] CI/CD pipeline with automated tests

## Documentation roadmap

As each phase is implemented, the corresponding doc will be updated:

| Doc | Phase |
|-----|-------|
| `07_NERParser.md` | Phase 5 |
| `08_SearchStrategies.md` | Phase 6 |
| `09_Elasticsearch.md` | Phase 6 |
| `10_MLRanking.md` | Phase 7 |
| `11_HierarchyValidation.md` | Phase 4 |
| `12_API.md` | Phase 8 |
| `14_PerformanceMetrics.md` | Benchmarks |
| `15_Deployment.md` | Docker / production |
