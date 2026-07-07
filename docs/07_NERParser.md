Query Processing
Requirements
Normalize user input
Convert to lowercase
Remove extra spaces
Remove unwanted punctuation
Expand common abbreviations
rd → road
st → street
apt → apartment
Handle spelling mistakes
Handle mixed casing
Handle multiple spaces
Tokenize query
Generate phrase combinations
Phase 2 — Entity Detection (NER)
Requirements

Extract:

Building Name
Flat Number
House Number
Road Name
Locality
Area
Village
City
District
State
Pincode
Landmark

Should support:

Partial addresses
Complete addresses
Only pincode
Only city
Mixed order addresses

## Run Commands

Use these commands from the project root while Elasticsearch work is still in progress:

```powershell
# Run the parser / NER tests only
c:/Vidushi/Indian_Add_Geo/venv/Scripts/python.exe -m pytest tests/test_parser.py

# Run parser tests together with the existing search coverage
c:/Vidushi/Indian_Add_Geo/venv/Scripts/python.exe -m pytest tests/test_parser.py tests/test_search.py

# Inspect a parsed address without needing Elasticsearch
c:/Vidushi/Indian_Add_Geo/venv/Scripts/python.exe -c "from parser.parser_pipeline import ParserPipeline; import json; print(json.dumps(ParserPipeline().parse('Flat 302 Lotus Heights Baner Pune 411045'), indent=2, ensure_ascii=False))"

# Inspect a pincode-only parse
c:/Vidushi/Indian_Add_Geo/venv/Scripts/python.exe -c "from parser.parser_pipeline import ParserPipeline; import json; print(json.dumps(ParserPipeline().parse('411045'), indent=2, ensure_ascii=False))"
```