"""Hash utilities for address fingerprinting."""

from __future__ import annotations

import hashlib


def compute_address_hash(normalized_address: str) -> str:
    """Return a stable SHA-256 hash for duplicate detection and caching."""
    digest = hashlib.sha256(normalized_address.encode("utf-8"))
    return digest.hexdigest()
