# Preprocessing (Phase 3)

## Objective

Transform the ingested **master dataset** into a **cleaned, validated, deduplicated** dataset ready for normalization, NER parsing, and Elasticsearch indexing.

Preprocessing performs **cleaning and structural normalization only** — it does not run ML models or geocoding.

## Input / output

| | Path |
|---|------|
| **Input** | `datasets/master/master_dataset.csv` |
| **Output** | `datasets/processed/cleaned_dataset.csv` |
| **Metadata** | `datasets/processed/preprocessing_metadata.json` |
| **Report** | `reports/preprocessing_report.json` |
| **Config** | `configs/preprocessing.yaml` |

## Run

```powershell
python scripts\preprocess_data.py
python -m pytest tests\test_preprocessing.py -v
```

---

## Pipeline steps (in order)

### 1. Remove duplicate rows

- **Module:** `preprocessing/deduplicator.py`
- Drops exact duplicate rows (all columns except `serial_number`)
- Keeps first occurrence

### 2. Remove empty rows

- **Module:** `preprocessing/cleaner.py`
- Removes rows where every cell is null or blank

### 3. Remove empty columns

- **Module:** `preprocessing/cleaner.py`
- Drops columns that are entirely null/blank

### 4. Remove invalid characters

- **Modules:** `preprocessing/cleaner.py`, `preprocessing/unicode_normalizer.py`
- Strips invisible unicode (zero-width spaces, BOM, etc.)
- Collapses repeated commas inside cell values
- Trims and collapses whitespace

### 5. Null normalization

- **Module:** `preprocessing/null_handler.py`
- Converts these to `pd.NA`:

  `NULL`, `null`, `None`, `NA`, `N/A`, `nan`, `-`, `--`, `.`, empty string

### 6. Fill missing values (where possible)

- **Module:** `preprocessing/null_handler.py`
- Builds code→name lookups from rows where both exist
- Fills missing names from codes:

  | Code column | Name column |
  |-------------|-------------|
  | `state_code` | `state_name` |
  | `district_code` | `district_name` |
  | `subdistrict_code` | `subdistrict_name` |
  | `block_code` | `block_name` |
  | `locality_code` | `locality` |

### 7–9. String normalization

- **Module:** `preprocessing/normalizer.py`
- Trim leading/trailing spaces
- Collapse multiple spaces
- Title-case every word (`MAHARASHTRA` → `Maharashtra`)

### 10. Abbreviation expansion

- **Module:** `preprocessing/abbreviation_expander.py`
- Dictionary: `datasets/dictionaries/abbreviations.json`
- Examples: `Rd` → `Road`, `St` → `Street`, `Ngr` → `Nagar`, `BO` → `Branch Office`
- Applied to: `office_name`, `road_name`, `building_name`, `locality`, `local_body_name`

### 11. Special symbol normalization

- **Module:** `preprocessing/symbol_normalizer.py`
- `sector - 21` → `sector 21`
- Removes stray special characters while keeping alphanumeric text

### 12. Geographic name standardization

- **Module:** `preprocessing/normalizer.py`
- Standardizes `state_name`, `district_name`, `city_name`, `subdistrict_name`, `locality`
- Uses hierarchy CSVs if available; otherwise builds canonical map from dataset

### 13. Pincode validation

- **Module:** `preprocessing/normalizer.py`
- **Rule:** `^[1-9][0-9]{5}$`
- Exactly 6 digits, numeric only, cannot start with 0
- Invalid pincodes → `pd.NA`

### 14. Coordinate validation

- **Module:** `preprocessing/normalizer.py`
- Latitude: −90 to 90
- Longitude: −180 to 180
- Invalid values → `pd.NA` with **log warning**

### 15. Build full address

- **Module:** `preprocessing/address_builder.py`
- Composes `full_address` from (in order):

  ```
  building_name → road_name → locality → city_name → district_name → state_name → pincode
  ```

- Separator: `, ` (configurable in YAML)

### 16. Address hash

- **Module:** `preprocessing/address_deduplicator.py`, `utils/hash_utils.py`
- Normalizes address text (lowercase, remove punctuation/commas)
- Computes SHA-256 → `address_hash`
- Used for duplicate detection, fast lookup, caching

### 17. Duplicate address detection

- **Module:** `preprocessing/address_deduplicator.py`
- Treats as duplicates:

  | Address A | Address B |
  |-----------|-----------|
  | `TCS Hinjewadi` | `TCS, Hinjewadi` |
  | `Sector 21` | `Sector-21` |

- Keeps first row per `address_hash`

### 18. Row quality score

- **Module:** `preprocessing/quality_scorer.py`
- Column `quality_score` (0–100) based on field completeness

  | Field | Weight |
  |-------|--------|
  | `locality` | 15 |
  | `city_name` | 15 |
  | `district_name` | 15 |
  | `state_name` | 15 |
  | `building_name` | 10 |
  | `road_name` | 10 |
  | `pincode` | 10 |
  | `latitude` | 5 |
  | `longitude` | 5 |

### 19. Dataset statistics

- **Module:** `preprocessing/statistics.py`
- Total rows/columns, null percentages, unique counts
- Quality score min/max/mean/median
- Pincode and coordinate coverage
- Duplicate hash count

### 20. Report generation

- **Module:** `preprocessing/report_generator.py`
- Writes `reports/preprocessing_report.json` with pipeline metadata + dataset statistics

---

## Output columns added

| Column | Type | Description |
|--------|------|-------------|
| `full_address` | string | Composed readable address |
| `address_hash` | string | SHA-256 hex digest |
| `quality_score` | float | 0–100 completeness score |

---

## Example report structure

```json
{
  "report_type": "preprocessing",
  "generated_at": "2026-07-03T…",
  "pipeline": { "statistics": { … }, "dataset_statistics": { … } },
  "dataset_statistics": {
    "total_rows": 4536021,
    "quality_score": { "mean": 42.5, "median": 38.0 },
    "null_percentages": { … },
    "unique_counts": { "state_name": 36, "pincode": 19000 }
  }
}
```

---

## Module reference

```
preprocessing/
├── deduplicator.py
├── cleaner.py
├── unicode_normalizer.py
├── null_handler.py
├── abbreviation_expander.py
├── symbol_normalizer.py
├── normalizer.py
├── address_builder.py
├── address_deduplicator.py
├── quality_scorer.py
├── statistics.py
├── report_generator.py
└── preprocessing_pipeline.py
```
