# Indian Address Search Engine
## Remaining Development Tasks

---

# Phase 1: Query Understanding (Highest Priority)

## 1. Entity Detection
- Improve Building Name extraction
- Improve Office Name extraction
- Improve Road Name extraction
- Improve Locality extraction
- Improve City/District detection
- Detect Landmark names
- Detect House/Flat numbers
- Detect Pincode accurately

---

## 2. Query Normalization
- Expand abbreviations
  - Rd → Road
  - St → Street
  - Apt → Apartment
- Remove unwanted punctuation
- Handle mixed uppercase/lowercase
- Remove duplicate spaces
- Handle spelling variations
- Handle common address abbreviations

---

## 3. Intent Detection
Support:

- Full Address Search
- Building Search
- Office Search
- Road Search
- Locality Search
- City Search
- State Search
- Pincode Search
- Landmark Search
- Nearby Search

---

# Phase 2: Elasticsearch Retrieval

## Improve Query Builder

### Exact Search
- Exact Building match
- Exact Office match
- Exact Locality match
- Exact Road match
- Exact City match

### Phrase Search
- Better match_phrase queries
- Adjustable phrase slop
- Preserve word order

### Fuzzy Search
- Handle spelling mistakes
- Handle missing words
- Handle extra words
- Handle OCR mistakes

### Autocomplete
- Prefix search
- Edge Ngram optimization
- Typing suggestions

### Multi Match
Search simultaneously across:

- searchable_text
- full_address
- building_name
- office_name
- road_name
- locality
- city_name
- district_name
- state_name

---

## Boosting

Increase score for

- Building name
- Office name
- Pincode
- Locality
- Road name
- City
- Quality score

---

## Filters

Support filters for

- State
- District
- City
- Locality
- Pincode
- Building
- Office
- Geo Distance

---

# Phase 3: Candidate Retrieval

(Currently implemented)

Need improvements:

- Retrieve Top 100 candidates
- Remove duplicate candidates
- Better confidence calculation
- Better score normalization
- Improve retrieval speed

---

# Phase 4: ML Re-ranking

## Feature Engineering

Create ML features:

- BM25 Score
- Exact Building Match
- Exact Office Match
- Exact Locality Match
- Exact Road Match
- Exact City Match
- Exact State Match
- Exact Pincode Match
- Token Overlap
- Jaccard Similarity
- Cosine Similarity
- Levenshtein Distance
- Query Length
- Candidate Length
- Geo Distance
- Quality Score
- Source Reliability

---

## Dataset Creation

Generate training dataset

Input:

Query

Candidate

Output:

Relevant (1)

Not Relevant (0)

---

## Train ML Model

Possible models

- XGBoost ⭐ (Recommended)
- LightGBM
- CatBoost
- Random Forest

---

## Prediction

For every candidate

Predict:

Relevance Score

Sort candidates using ML score

Return Top K

---

# Phase 5: Final Ranking

Combine

- BM25 Score
- ML Score
- Quality Score
- Exact Match Score
- Geo Score

Generate Final Confidence Score

Return:

- Best Address
- Confidence
- Match Explanation

---

# Phase 6: API Development

Create endpoints

- Search Address
- Reverse Geocode
- Autocomplete
- Suggest Address
- Nearby Search
- Health Check

---

# Phase 7: Performance Optimization

- Query caching
- Connection pooling
- Batch inference
- Elasticsearch profiling
- Reduce response time
- Parallel feature extraction
- Parallel ML inference

---

# Phase 8: Testing

Write tests for

- Entity Detector
- Query Parser
- Query Builder
- Search Service
- Candidate Retrieval
- ML Re-ranker
- API
- End-to-End Search

---

# Phase 9: Deployment

- FastAPI Server
- Docker
- IIS/Nginx
- Elasticsearch
- Logging
- Monitoring
- Production Configuration

---

# Final Pipeline

User Query
↓
Normalize Query
↓
Entity Detection
↓
Intent Detection
↓
Query Builder
↓
Elasticsearch Retrieval (Top 100)
↓
Feature Engineering
↓
ML Re-ranker (XGBoost)
↓
Final Ranking
↓
Confidence Score
↓
Best Address Returned

---

# Current Progress

## ✅ Completed
- Data Ingestion
- Data Cleaning
- Elasticsearch Setup
- Index Creation
- Custom Mapping
- Bulk Indexing (~1.9M records)
- Search Service
- Query Parser
- Entity Detection (building/road/locality/city/pincode/state/village/block/taluka)
- Office Name detection
- Landmark detection
- Intent Detection (incl. Office & Nearby intents)
- Query Normalization (abbreviations, spelling corrections, dedupe)
- Query Builder (exact/phrase/fuzzy/autocomplete/multi_match + boosting + filters + geo)
- Candidate Retrieval (Top 100) + Deduplication
- ML Feature Engineering (ranking/feature_engineering.py)
- Re-ranker (XGBoost with heuristic fallback)
- Final Ranking + Confidence Score
- FastAPI APIs (search, autocomplete, suggest, nearby, reverse-geocode, health)
- CLI Search
- Dry Run Mode
- Docker / docker-compose deployment
- Test Suite (search, API, parser, preprocessing, ingestion, hierarchy)

- ML training pipeline: self-supervised dataset generator (scripts/build_ranking_dataset.py) + XGBoost trainer (scripts/train_ranker.py); model auto-loaded by the search pipeline

## 🚧 In Progress / Optional
- Performance tuning (caching, batch inference)
- Improving ML model quality with more/real labeled queries

## ❌ Remaining
- Production hardening (auth, rate limiting, monitoring dashboards)

See `docs/18_EndToEndRunGuide.md` for the full start-to-end command sequence.