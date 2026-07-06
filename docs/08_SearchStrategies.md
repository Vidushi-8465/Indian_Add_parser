Since your project is **Production-Grade Indian Address Geocoding & Search System**, the search engine should do much more than simply execute an Elasticsearch query. It should act as an intelligent retrieval layer between the user and Elasticsearch.

## Search Engine Requirements

### 1. Query Input

* Accept raw user address queries.
* Accept complete or partial addresses.
* Accept noisy/incomplete inputs.
* Support English and Indian address abbreviations.
* Handle extra spaces and punctuation.

---

### 2. Query Normalization

* Convert to lowercase.
* Remove extra spaces.
* Remove unwanted symbols.
* Normalize punctuation.
* Expand abbreviations (Rd → Road, St → Street, Apt → Apartment, etc.).
* Normalize state names (MH → Maharashtra).
* Normalize common spelling variations.

---

### 3. Query Tokenization

* Split query into tokens.
* Preserve important multi-word phrases.
* Separate numbers from text.
* Detect alphanumeric building numbers.

Example:

```
Flat 302 Lotus Heights Baner Pune 411045

↓

["Flat","302","Lotus","Heights","Baner","Pune","411045"]
```

---

### 4. Entity Detection (Rule-based initially)

Identify:

* Building Name
* Flat/House Number
* Road Name
* Locality
* Village
* Block
* Taluka/Subdistrict
* District
* City
* State
* Pincode

---

### 5. Query Intent Detection

Detect search type.

Examples:

```
411045
→ Pincode Search

Mumbai
→ City Search

Baner Pune
→ Locality Search

Lotus Heights
→ Building Search

Flat 302 Baner Pune
→ Full Address Search
```

---

### 6. Query Validation

* Detect invalid pincodes.
* Detect impossible inputs.
* Reject empty queries.
* Check minimum token count.
* Remove duplicate words.

---

### 7. Query Enrichment

Automatically infer missing information.

Example

```
411045

↓

Pune
Maharashtra
```

Example

```
Mumbai

↓

Maharashtra
```

---

### 8. Elasticsearch Query Builder

Generate optimized queries using:

* Multi-match search
* Match Phrase
* Exact Match
* Prefix Search
* Autocomplete
* Fuzzy Search
* Boolean Queries
* Field Boosting
* Filters

---

### 9. Boosting Logic

Prioritize:

* Exact building name
* Exact pincode
* Exact city
* Exact locality
* Exact road
* Exact state
* High quality_score
* Complete addresses

---

### 10. Candidate Retrieval

Retrieve only the Top-N candidates (e.g., Top 100) from Elasticsearch for further ranking.

---

### 11. Result Re-ranking

Re-rank retrieved addresses using:

* Elasticsearch score
* Exact token matches
* Phrase matches
* Address completeness
* Quality score
* Pincode match
* State match
* City match
* Locality match

(ML re-ranking can be added later.)

---

### 12. Confidence Score

Generate a confidence score for each result.

Example:

```
Address:
Lotus Heights, Baner, Pune

Confidence:
98.7%
```

---

### 13. Parsed Output

Return structured entities.

Example

```json
{
  "building_name": "Lotus Heights",
  "road_name": "Baner Road",
  "locality": "Baner",
  "city": "Pune",
  "district": "Pune",
  "state": "Maharashtra",
  "pincode": "411045"
}
```

---

### 14. Search Modes

Support:

* Full Address Search
* Building Search
* Locality Search
* Road Search
* Village Search
* Block Search
* City Search
* District Search
* State Search
* Pincode Search

---

### 15. Two-Way Search (Your Project Requirement)

Support both:

**Forward Search**

```
State
 ↓
District
 ↓
City
 ↓
Locality
 ↓
Road
 ↓
Building
 ↓
Pincode
```

**Reverse Search**

```
Pincode
 ↓
State
 ↓
District
 ↓
City
 ↓
Locality
 ↓
Road
 ↓
Building
```

---

### 16. Autocomplete

Return suggestions while typing.

Example

```
Pun

↓

Pune
Pune Cantonment
Pune Division
```

---

### 17. Spell Correction

Handle common typing mistakes.

Examples:

```
Mubmai
↓

Mumbai

Banglore
↓

Bangalore

Maharastra
↓

Maharashtra
```

---

### 18. Synonym Handling

Recognize equivalent terms.

Examples:

* Rd ↔ Road
* St ↔ Street
* Apt ↔ Apartment
* Po ↔ Post Office
* PS ↔ Police Station
* GP ↔ Gram Panchayat

---

### 19. Performance Requirements

* Average search latency < 100 ms
* Autocomplete latency < 50 ms
* Support millions of indexed addresses
* Concurrent request handling
* Efficient pagination

---

### 20. Logging & Monitoring

Log:

* User query
* Parsed entities
* Query type
* Elasticsearch execution time
* Number of hits
* Top result
* Confidence score
* Errors and warnings

---

## Output Format

The search engine should return a structured response like:

```json
{
  "query": "Flat 302 Lotus Heights Baner Pune",
  "normalized_query": "flat 302 lotus heights baner pune",
  "intent": "FULL_ADDRESS_SEARCH",
  "parsed_entities": {
    "building_name": "Lotus Heights",
    "locality": "Baner",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411045"
  },
  "results": [
    {
      "full_address": "...",
      "score": 98.5,
      "confidence": 0.99
    }
  ],
  "execution_time_ms": 42
}
```

These requirements create a solid foundation for the next phase of your project and also make it straightforward to integrate your planned ML components (NER, intent classification, and ML-based re-ranking) without redesigning the search engine later.

## Run Commands

Use these commands from the project root:

```powershell
# Run the search package tests
c:/Vidushi/Indian_Add_Geo/venv/Scripts/python.exe -m pytest tests/test_search.py

# Run the search package together with the existing ES/API coverage
c:/Vidushi/Indian_Add_Geo/venv/Scripts/python.exe -m pytest tests/test_search.py tests/test_elasticsearch.py tests/test_api.py

# Inspect query normalization, entity parsing, and the generated ES body without calling Elasticsearch
c:/Vidushi/Indian_Add_Geo/venv/Scripts/python.exe -m search.search_service --query "Flat 302 Lotus Heights Baner Pune 411045" --dry-run

# Inspect a pure pincode query
c:/Vidushi/Indian_Add_Geo/venv/Scripts/python.exe -m search.search_service --query "411045" --dry-run
```
