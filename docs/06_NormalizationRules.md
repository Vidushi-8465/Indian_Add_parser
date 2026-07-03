# Normalization Rules

This document describes text and schema normalization rules used in **ingestion (Phase 2)** and **preprocessing (Phase 3)**.

---

## Phase 2 — Column name normalization (ingestion)

### Column name cleaning

Before alias matching, column names are normalized:

1. Lowercase
2. Remove `*` and parenthetical suffixes — `State Name (In English)` → `state name`
3. Replace `.`, `_`, `-`, `/` with spaces — `S.No.` → `s no`
4. Collapse multiple spaces

### Alias matching priority

1. **Exact match** against `configs/ingestion.yaml` aliases (confidence 100%)
2. **Fuzzy match** via RapidFuzz (threshold ≥ 88%)

### Subdistrict protection rule

Columns containing `subdistrict`, `sub-district`, `tehsil`, or `taluk` **must not** fuzzy-match to `district_*` fields.

| Source column | Maps to |
|---------------|---------|
| `District Code` | `district_code` |
| `District Name` | `district_name` |
| `Subdistrict Code` | `subdistrict_code` |
| `Sub-District Name (In English)` | `subdistrict_name` |
| `SubDistrict Name` | `subdistrict_name` |

### Common alias examples

| Source variations | Standard column |
|-------------------|-----------------|
| `Pin Code`, `PIN`, `Postal_Code`, `ZipCode` | `pincode` |
| `statename`, `State Name (In English)` | `state_name` |
| `City/Town`, `city` | `city_name` |
| `Village Name (In English)`, `village` | `locality` |
| `officename`, `Post Office` | `office_name` |
| `circlename` | `circle_name` |

Full alias list: `configs/ingestion.yaml` → `column_aliases`

---

## Phase 3 — Cell value normalization (preprocessing)

### Null-like values

All of the following become `pd.NA`:

```
(empty), null, none, na, n/a, nan, -, --, .
```

Case-insensitive matching.

### Whitespace rules

- Strip leading and trailing spaces
- Collapse multiple internal spaces to one
- Remove invisible unicode characters (zero-width, BOM, soft hyphen)

### Special symbol rules

| Before | After |
|--------|-------|
| `sector - 21` | `sector 21` |
| `Block - A` | `Block A` |
| `TCS,,, Hinjewadi` | `TCS, Hinjewadi` |

### Title case rule

Every word is title-cased for name columns:

```
andaman and nicobar islands  →  Andaman And Nicobar Islands
TELANGANA                    →  Telangana
```

Applied to: state, district, city, locality, road, building, office, panchayat, region, division, circle names.

### Abbreviation expansion

Word-boundary replacement from `datasets/dictionaries/abbreviations.json`:

| Abbreviation | Expansion |
|--------------|-----------|
| `rd` | `Road` |
| `st`, `str` | `Street` |
| `ngr`, `ng` | `Nagar` |
| `col` | `Colony` |
| `sec` | `Sector` |
| `bo` | `Branch Office` |
| `po` | `Post Office` |
| `gp` | `Gram Panchayat` |

### Pincode rule

```
Regex: ^[1-9][0-9]{5}$

Valid:   500001, 411057, 744101
Invalid: 012345 (starts with 0), 50001 (5 digits), abc123
```

Invalid → set to `pd.NA`

### Coordinate rules

| Field | Valid range | Invalid action |
|-------|-------------|----------------|
| Latitude | −90.0 to 90.0 | Set to `pd.NA`, log warning |
| Longitude | −180.0 to 180.0 | Set to `pd.NA`, log warning |

### Address deduplication key

For duplicate address detection, text is normalized:

1. Lowercase
2. Remove all punctuation
3. Collapse spaces

```
"TCS, Hinjewadi"  →  "tcs hinjewadi"
"TCS Hinjewadi"   →  "tcs hinjewadi"   (same hash)
```

### Full address composition

```
full_address = join(", ", non-empty parts of:
  building_name, road_name, locality, city_name,
  district_name, state_name, pincode)
```

### Address hash

```
address_hash = SHA256(normalized_full_address)
```

Used for duplicate detection, fast lookup, and caching.

---

## Hierarchy fill rules

When a **code** is present but the **name** is missing, fill from lookup built from other rows:

```
state_code     → state_name
district_code  → district_name
subdistrict_code → subdistrict_name
block_code     → block_name
locality_code  → locality
```

---

## Configuration reference

| Rule set | Config file |
|----------|-------------|
| Column aliases & schema | `configs/ingestion.yaml` |
| Null values, validation, quality weights | `configs/preprocessing.yaml` |
| Abbreviations | `datasets/dictionaries/abbreviations.json` |
