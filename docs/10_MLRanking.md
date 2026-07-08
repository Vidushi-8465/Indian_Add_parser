 Phase 1: Prepare Training Data
- Create a labeled dataset.
- Each row = **(query, candidate address)**.
- Add a relevance label (e.g. 0–3 or binary 0/1).
- Include both positive and negative examples.

 Phase 2: Feature Engineering
For every candidate, generate features such as:
 Text Similarity
- Query vs Full Address similarity
- Query vs Building Name similarity
- Query vs Road Name similarity
- Query vs Locality similarity
- Query vs City similarity
- Query vs District similarity
- Query vs State similarity

 Exact Match Features
- Building exact match
- Road exact match
- Locality exact match
- City exact match
- State exact match
- Pincode exact match

 Fuzzy Features
- Fuzzy ratio
- Partial ratio
- Token sort ratio
- Token set ratio

 Token Features
- Common token count
- Token overlap percentage
- Jaccard similarity

 Elasticsearch Features
- BM25 score
- Quality score
- Candidate rank from ES
- Candidate retrieval position

Geographic Features
- Latitude available
- Longitude available
- Geo distance (if query contains coordinates)

Phase 3: Feature Builder
Convert every query–candidate pair into a numeric feature vector.
Handle missing values.
Normalize features if required.
Save feature matrix.
Phase 4: Model Selection

Choose one ranking model:

XGBoost Ranker (recommended)
LightGBM Ranker
CatBoost Ranker
Phase 5: Training
Split train/validation data.
Train the ranking model.
Save the trained model (.json or .pkl).
Phase 6: Inference

For every search:

User Query
      ↓
Top 100 ES Candidates
      ↓
Generate Features
      ↓
Load Trained Model
      ↓
Predict Relevance Score
      ↓
Sort by Score
      ↓
Return Top 20
Phase 7: Confidence Score

Generate a confidence value based on:

ML prediction score
BM25 score
Exact field matches
Quality score

Example:

Score > 0.95  → Exact Match
0.80–0.95     → High Confidence
0.60–0.80     → Medium Confidence
<0.60         → Low Confidence
Phase 8: Evaluation

Measure search quality using ranking metrics:

NDCG@10
MRR (Mean Reciprocal Rank)
Precision@10
Recall@100
Top-1 Accuracy
Top-5 Accuracy

## Commands to run

```powershell
cd c:\Vidushi\Indian_Add_Geo
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```powershell
# Validate the search + reranking flow
python -m pytest tests\test_search.py -v

# Validate Elasticsearch integration used by the search service
python -m pytest tests\test_elasticsearch.py tests\test_api.py -v
```

```powershell
# Dry-run the ML search pipeline without hitting Elasticsearch
python search\search_service.py --query "MG Road Pune" --dry-run

# Run a live search once Elasticsearch is available
python search\search_service.py --query "MG Road Pune" --size 20
```

```powershell
# Point inference at a trained ranking model when you have one
$env:RANKING_MODEL_PATH = "c:\Vidushi\Indian_Add_Geo\models\ranking_model.json"
```
