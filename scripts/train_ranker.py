"""Train the XGBoost learning-to-rank re-ranker (Phase 4/5).

Consumes the JSONL dataset produced by ``scripts/build_ranking_dataset.py`` and
trains an ``XGBRanker`` via ``ranking.ranker.MLRanker``. The trained model and its
feature-order sidecar are saved to ``models/ranking_model.json`` (the path the
search pipeline auto-loads), and validation ranking metrics are printed.
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

from ranking.ranker import MLRanker
from ranking.scorer import RankingEvaluator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the ML ranking model.")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "datasets" / "ranking" / "train.jsonl")
    parser.add_argument("--model-out", type=Path, default=PROJECT_ROOT / "models" / "ranking_model.json")
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def load_groups(dataset_path: Path) -> tuple[dict[int, list[dict]], list[str]]:
    """Load JSONL rows grouped by group id, plus the ordered feature-name union."""
    groups: dict[int, list[dict]] = {}
    feature_names: list[str] = []
    seen: set[str] = set()
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            groups.setdefault(int(row["group"]), []).append(row)
            for name in row.get("features", {}):
                if name not in seen:
                    seen.add(name)
                    feature_names.append(name)
    return groups, feature_names


def flatten(group_ids: list[int], groups: dict[int, list[dict]]) -> tuple[list[dict], list[int], list[int]]:
    feature_dicts: list[dict] = []
    labels: list[int] = []
    group_sizes: list[int] = []
    for group_id in group_ids:
        rows = groups[group_id]
        if not rows:
            continue
        for row in rows:
            feature_dicts.append(row["features"])
            labels.append(int(row["label"]))
        group_sizes.append(len(rows))
    return feature_dicts, labels, group_sizes


def main() -> int:
    args = parse_args()
    if not args.dataset.exists():
        print(f"ERROR: dataset not found: {args.dataset}", flush=True)
        print("Run scripts/build_ranking_dataset.py first.", flush=True)
        return 1

    groups, feature_names = load_groups(args.dataset)
    group_ids = list(groups.keys())
    if not group_ids:
        print("ERROR: dataset is empty.", flush=True)
        return 1

    rng = random.Random(args.seed)
    rng.shuffle(group_ids)
    val_count = max(1, int(len(group_ids) * args.val_fraction)) if len(group_ids) > 1 else 0
    val_ids = group_ids[:val_count]
    train_ids = group_ids[val_count:]

    train_features, train_labels, train_groups = flatten(train_ids, groups)
    print(
        f"Training on {len(train_ids)} groups / {len(train_features)} pairs; "
        f"validating on {len(val_ids)} groups.",
        flush=True,
    )

    ranker = MLRanker(model_path=args.model_out)
    # Start from a clean slate so a previously trained model is not reused.
    ranker.model = None
    ranker._features_locked = False
    ranker.feature_names = feature_names

    try:
        ranker.fit(train_features, train_labels, group=train_groups, model_path=args.model_out)
    except RuntimeError as error:
        print(f"ERROR: {error}", flush=True)
        print("Install xgboost:  pip install xgboost", flush=True)
        return 1

    print(f"Model saved to {args.model_out}", flush=True)

    # Validation metrics (averaged across held-out query groups).
    if val_ids:
        aggregate: dict[str, float] = {}
        evaluated = 0
        for group_id in val_ids:
            rows = groups[group_id]
            if not any(int(r["label"]) > 0 for r in rows):
                continue
            scores = ranker.predict([r["features"] for r in rows])
            labels = [int(r["label"]) for r in rows]
            metrics = RankingEvaluator.evaluate(labels, scores)
            for key, value in metrics.items():
                aggregate[key] = aggregate.get(key, 0.0) + value
            evaluated += 1

        if evaluated:
            print(f"\nValidation metrics (mean over {evaluated} groups):", flush=True)
            for key in sorted(aggregate):
                print(f"  {key:16s}: {aggregate[key] / evaluated:.4f}")
        else:
            print("No validation groups with a positive label to evaluate.", flush=True)

    print("\nDone. The search pipeline will now use this model automatically.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
