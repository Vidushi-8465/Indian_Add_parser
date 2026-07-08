"""Text similarity helpers for ranking feature generation."""

from __future__ import annotations

import re
from typing import Iterable

from rapidfuzz import fuzz

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(_TOKEN_RE.findall(value.casefold()))


def tokenize(value: str | None) -> list[str]:
    return normalize_text(value).split()


def exact_match(left: str | None, right: str | None) -> int:
    if not left or not right:
        return 0
    return int(normalize_text(left) == normalize_text(right))


def safe_ratio(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return fuzz.ratio(normalize_text(left), normalize_text(right)) / 100.0


def partial_ratio(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return fuzz.partial_ratio(normalize_text(left), normalize_text(right)) / 100.0


def token_sort_ratio(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return fuzz.token_sort_ratio(normalize_text(left), normalize_text(right)) / 100.0


def token_set_ratio(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return fuzz.token_set_ratio(normalize_text(left), normalize_text(right)) / 100.0


def common_token_count(left: str | None, right: str | None) -> float:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    return float(len(left_tokens & right_tokens))


def token_overlap_percent(left: str | None, right: str | None) -> float:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    if not left_tokens:
        return 0.0
    return float(len(left_tokens & right_tokens) / len(left_tokens))


def jaccard_similarity(left: str | None, right: str | None) -> float:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return float(len(left_tokens & right_tokens) / len(union))


def score_sequence_similarity(left: str | None, right: str | None) -> dict[str, float]:
    return {
        "ratio": safe_ratio(left, right),
        "partial_ratio": partial_ratio(left, right),
        "token_sort_ratio": token_sort_ratio(left, right),
        "token_set_ratio": token_set_ratio(left, right),
        "common_token_count": common_token_count(left, right),
        "token_overlap_percent": token_overlap_percent(left, right),
        "jaccard_similarity": jaccard_similarity(left, right),
        "exact_match": float(exact_match(left, right)),
    }


def mean_score(values: Iterable[float]) -> float:
    values = list(values)
    if not values:
        return 0.0
    return float(sum(values) / len(values))
