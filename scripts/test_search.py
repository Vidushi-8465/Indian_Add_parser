from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from es_index.client import build_elasticsearch_client
from utils.constants import DEFAULT_ELASTICSEARCH_CONFIG
from utils.file_utils import load_yaml_config

config = load_yaml_config(DEFAULT_ELASTICSEARCH_CONFIG)

client = build_elasticsearch_client(config)

index = config["index"]["name"]

while True:

    q = input("\nSearch Address : ")

    if q == "":
        break

    body = {
        "size": 5,
        "query": {
            "multi_match": {
                "query": q,
                "fields": [
                    "full_address^5",
                    "searchable_text^4",
                    "building_name^3",
                    "road_name^3",
                    "locality^3",
                    "city_name^2",
                    "district_name^2",
                    "state_name",
                    "pincode"
                ]
            }
        }
    }

    response = client.search(index=index, body=body)

    print()

    for hit in response["hits"]["hits"]:

        print("=" * 70)
        print("Score :", hit["_score"])

        source = hit["_source"]

        print("Address :", source.get("full_address"))
        print("Pincode :", source.get("pincode"))
        print("State   :", source.get("state_name"))