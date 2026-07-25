"""Build a learning-to-rank training dataset for the ML re-ranker (Phase 4).

Strategy (self-supervised, no manual labelling needed):

1. Sample real addresses from ``datasets/processed/cleaned_dataset.csv``. Each row
   is a known-correct address with a stable ``address_hash``.
2. Synthesize a realistic, *degraded* user query from each address (drop tokens,
   abbreviate, add typos) — this simulates a messy search whose correct answer is
   that address.
3. Retrieve the top-N Elasticsearch candidates for the synthetic query using the
   real search pipeline.
4. Label each (query, candidate) pair: relevant (1) if the candidate's
   ``address_hash`` matches the source address, otherwise 0.
5. Emit one JSONL row per pair with the engineered features + label + group id.

Requires a running Elasticsearch with the ``indian_addresses`` index populated.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from es_index.client import build_elasticsearch_client, test_connection
from ranking.feature_engineering import RankingFeatureBuilder
from search.search_service import SearchService
from utils.constants import DEFAULT_ELASTICSEARCH_CONFIG
from utils.file_utils import load_yaml_config

USECOLS = [
    "full_address",
    "address_hash",
    "pincode",
    "locality",
    "city_name",
    "district_name",
    "state_name",
    "quality_score",
]

ABBREVIATE = {
    "road": "rd",
    "street": "st",
    "nagar": "ngr",
    "colony": "col",
    "district": "dist",
    "post office": "po",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an ML ranking training dataset.")
    parser.add_argument("--config", type=Path, default=DEFAULT_ELASTICSEARCH_CONFIG)
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "datasets" / "processed" / "cleaned_dataset.csv")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "datasets" / "ranking" / "train.jsonl")
    parser.add_argument("--num-queries", type=int, default=1500, help="Number of source addresses to sample.")
    parser.add_argument("--max-candidates", type=int, default=40, help="Max candidates kept per query (positive always kept).")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def introduce_typo(text: str, rng: random.Random) -> str:
    words = text.split()
    long_words = [index for index, word in enumerate(words) if len(word) >= 4]
    if not long_words:
        return text
    index = rng.choice(long_words)
    word = words[index]
    position = rng.randrange(len(word) - 1)
    kind = rng.random()
    if kind < 0.5:  # drop a character
        word = word[:position] + word[position + 1 :]
    else:  # swap two adjacent characters
        word = word[:position] + word[position + 1] + word[position] + word[position + 2 :]
    words[index] = word
    return " ".join(words)


def synthesize_query(row: pd.Series, rng: random.Random) -> str | None:
    full_address = str(row.get("full_address") or "").strip()
    if not full_address:
        return None

    components = [part.strip() for part in full_address.split(",") if part.strip()]
    if not components:
        return None

    # Always keep the most specific component; keep the rest probabilistically.
    kept = [components[0]]
    for component in components[1:]:
        if rng.random() < 0.6:
            kept.append(component)

    text = " ".join(kept).lower()

    # Occasionally abbreviate to mimic real user input.
    if rng.random() < 0.4:
        for full, short in ABBREVIATE.items():
            if full in text:
                text = text.replace(full, short)
                break

    # Optionally append the pincode.
    pincode = str(row.get("pincode") or "").strip()
    if pincode.isdigit() and len(pincode) == 6 and rng.random() < 0.5:
        text = f"{text} {pincode}"

    # Occasionally add a typo.
    if rng.random() < 0.3:
        text = introduce_typo(text, rng)

    text = text.strip()
    return text or None


def build_rows_for_query(
    service: SearchService,
    feature_builder: RankingFeatureBuilder,
    query: str,
    gold_hash: str,
    max_candidates: int,
) -> list[dict] | None:
    analysis = service.analyze_query(query)
    plan = service.build_search_plan(query=query)
    response = service.client.search(index=service.index_name, body=plan.query_body)
    hits = response.get("hits", {}).get("hits", [])
    candidates = service._retrieve_candidates(hits)
    if not candidates:
        return None

    # Keep the top candidates, but always retain the gold candidate if retrieved.
    kept = candidates[:max_candidates]
    if gold_hash and not any(c.address_hash == gold_hash for c in kept):
        gold = next((c for c in candidates if c.address_hash == gold_hash), None)
        if gold is not None:
            kept = kept[: max_candidates - 1] + [gold]

    if not any(c.address_hash == gold_hash for c in kept):
        return None  # no positive retrieved -> unusable for pairwise ranking

    feature_rows, _ = feature_builder.build_feature_matrix(
        analysis.normalized_query or query, analysis.parsed_entities, kept
    )
    rows: list[dict] = []
    for candidate, feature_row in zip(kept, feature_rows):
        rows.append(
            {
                "label": 1 if candidate.address_hash == gold_hash else 0,
                "features": feature_row.values,
                "query": query,
                "gold_hash": gold_hash,
                "candidate_hash": candidate.address_hash,
            }
        )
    return rows


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)

    config = load_yaml_config(args.config)
    client = build_elasticsearch_client(config)
    if not test_connection(client=client, config=config)["connected"]:
        print("ERROR: Elasticsearch is not reachable.", flush=True)
        return 1

    service = SearchService(client=client, config=config)
    feature_builder = RankingFeatureBuilder()

    print(f"Reading source addresses from {args.input} ...", flush=True)
    frame = pd.read_csv(args.input, usecols=lambda c: c in USECOLS, dtype=str, low_memory=False)
    frame = frame.dropna(subset=["full_address", "address_hash"])
    sample_size = min(args.num_queries, len(frame))
    sample = frame.sample(n=sample_size, random_state=args.seed)
    print(f"Sampled {sample_size} addresses. Generating candidates via Elasticsearch ...", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    group_id = 0
    written_pairs = 0
    covered = 0
    processed = 0
    with args.output.open("w", encoding="utf-8") as handle:
        for _, row in sample.iterrows():
            processed += 1
            query = synthesize_query(row, rng)
            if not query:
                continue
            gold_hash = str(row["address_hash"])
            try:
                rows = build_rows_for_query(service, feature_builder, query, gold_hash, args.max_candidates)
            except Exception as error:  # keep going on transient ES errors
                print(f"  skip query {query!r}: {error}", flush=True)
                continue
            if not rows:
                continue

            covered += 1
            for row_data in rows:
                row_data["group"] = group_id
                handle.write(json.dumps(row_data, ensure_ascii=False) + "\n")
                written_pairs += 1
            group_id += 1

            if processed % 100 == 0:
                print(f"  processed={processed} usable_groups={group_id} pairs={written_pairs}", flush=True)

    print("Dataset generation complete.", flush=True)
    print(f"  Source addresses processed: {processed}")
    print(f"  Usable query groups (gold retrieved): {group_id}")
    print(f"  Retrieval coverage: {covered}/{processed} ({(covered / processed * 100 if processed else 0):.1f}%)")
    print(f"  Total (query, candidate) pairs: {written_pairs}")
    print(f"  Output: {args.output}")
    if group_id == 0:
        print("WARNING: no usable groups produced; check that the index is populated.", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
