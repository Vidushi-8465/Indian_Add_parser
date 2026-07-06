from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from es_index.client import build_elasticsearch_client
from utils.constants import DEFAULT_ELASTICSEARCH_CONFIG
from utils.file_utils import load_yaml_config


def main():
    config = load_yaml_config(DEFAULT_ELASTICSEARCH_CONFIG)
    client = build_elasticsearch_client(config)

    index_name = config["index"]["name"]

    if not client.indices.exists(index=index_name):
        print("Index does not exist.")
        return

    stats = client.indices.stats(index=index_name)

    docs = stats["indices"][index_name]["total"]["docs"]
    store = stats["indices"][index_name]["total"]["store"]

    print("=" * 50)
    print("INDEX :", index_name)
    print("=" * 50)
    print("Documents :", docs["count"])
    print("Deleted   :", docs["deleted"])
    print("Size (MB) :", round(store["size_in_bytes"] / 1024 / 1024, 2))
    print("=" * 50)


if __name__ == "__main__":
    main()