# Dataset Description

## Raw data location

All raw files are **CSV format** in:

```
datasets/raw/csv/
```

Previously Excel files were converted to CSV before ingestion.

## Raw files (14 datasets)

| File | Content |
|------|---------|
| `all_india_pincode_directory_2025.csv` | Post offices, pincodes, lat/long |
| `All_Stateof_India_*.csv` | State codes and names |
| `All_Districtof_India_*.csv` | District codes and names |
| `All_Sub_Districtof_India_*.csv` | Sub-district (tehsil) records |
| `All_Villagesof_India_*.csv` | Village-level records |
| `All_Villagesof_India_Category_*.csv` | Villages with category and local body |
| `All_Blockof_Indiawith_Coverage_*.csv` | Development blocks and villages |
| `All_Village_Panchayat_Of_India_*.csv` | Panchayat hierarchy |
| `Cities_Towns_District_State_India.csv` | Urban cities and towns |
| `District_Subdistrict_Village_Gps_*.csv` | District → subdistrict → village → GP |
| `Pincodeto_Village_Mapping_*.csv` | Pincode to village mapping |
| `Pincodeto_Urban_Mapping_*.csv` | Pincode to urban local body |
| `Pincodeto_Urban_Mapping_Major_Minor_Version_*.csv` | Urban mapping with version fields |
| `Village_Gram_Panchayat_Mapping_*.csv` | Village to gram panchayat mapping |

## Master schema (after ingestion)

Standard columns defined in `configs/ingestion.yaml`:

### Identity and postal

- `serial_number`, `pincode`, `source_file`

### State

- `state_code`, `state_name`, `state_name_local`, `state_or_ut`
- `state_version`, `state_major_version`, `state_minor_version`

### District and sub-district

- `district_code`, `district_name`
- `subdistrict_code`, `subdistrict_name`, `subdistrict_version`

### Block, city, locality

- `block_code`, `block_name`
- `city_name`, `locality`, `locality_code`
- `village_category`, `village_status`, `village_version`

### Local body and panchayat

- `local_body_code`, `local_body_name`, `local_body_type_code`, `local_body_type_name`
- `district_panchayat_code`, `district_panchayat_name`
- `block_panchayat_code`, `block_panchayat_name`
- `gram_panchayat_code`, `gram_panchayat_name`

### Address components

- `road_name`, `building_name`, `office_name`, `office_type`

### Postal admin

- `delivery_status`, `urban_status`
- `region_name`, `division_name`, `circle_name`

### Geo

- `latitude`, `longitude`
- `census_2001_code`, `census_2011_code`

## Processed schema (after preprocessing)

All master columns plus:

| Column | Description |
|--------|-------------|
| `full_address` | Composed address string |
| `address_hash` | SHA-256 fingerprint for dedup and cache lookup |
| `quality_score` | 0–100 completeness score |

### Full address format

```
building_name, road_name, locality, city_name, district_name, state_name, pincode
```

Example:

```
TCS, Rajiv Gandhi Infotech Park, Hinjewadi, Pune, Pune, Maharashtra, 411057
```

## Dictionaries

| File | Purpose |
|------|---------|
| `datasets/dictionaries/abbreviations.json` | Rd, St, Nagar, BO, etc. |
| `datasets/dictionaries/stopwords.json` | (planned) |
| `datasets/dictionaries/road_types.json` | (planned) |

## Hierarchy reference files (optional)

Used for name standardization when present:

```
datasets/hierarchy/states.csv
datasets/hierarchy/districts.csv
datasets/hierarchy/cities.csv
```

If missing, canonical names are derived from the dataset itself.
