"""Regular expression patterns for validation."""

from __future__ import annotations

import re

PINCODE_PATTERN = re.compile(r"^[1-9][0-9]{5}$")

# Invisible / control characters often found in CSV exports
INVISIBLE_UNICODE_PATTERN = re.compile(
    r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\u00ad]"
)

# Repeated commas inside a cell value
EXTRA_COMMA_PATTERN = re.compile(r",{2,}")

# Hyphen/dash between words and numbers: "sector - 21" -> "sector 21"
DASH_BETWEEN_TOKENS_PATTERN = re.compile(r"\s*[-–—]\s*")

# Punctuation to remove for duplicate-address matching (keep alphanumeric + spaces)
DEDUP_PUNCTUATION_PATTERN = re.compile(r"[^\w\s]", re.UNICODE)
