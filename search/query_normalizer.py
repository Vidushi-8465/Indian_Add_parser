"""Query normalization helpers for address search."""

from __future__ import annotations

import re


class QueryNormalizer:
    """Normalize noisy address queries into a search-friendly form."""

    _PUNCTUATION_PATTERN = re.compile(r"[^\w\s]")
    _WHITESPACE_PATTERN = re.compile(r"\s+")

    ABBREVIATIONS = {
        "apt": "apartment",
        "apt.": "apartment",
        "blk": "block",
        "blk.": "block",
        "bldg": "building",
        "bldg.": "building",
        "dist": "district",
        "dist.": "district",
        "hno": "house number",
        "h.no": "house number",
        "po": "post office",
        "p.o": "post office",
        "ps": "police station",
        "rd": "road",
        "rd.": "road",
        "st": "street",
        "st.": "street",
        "tal": "taluka",
        "teh": "taluka",
        "vill": "village",
    }

    STATE_ABBREVIATIONS = {
        "ap": "andhra pradesh",
        "as": "assam",
        "br": "bihar",
        "cg": "chhattisgarh",
        "ch": "chandigarh",
        "dl": "delhi",
        "ga": "goa",
        "gj": "gujarat",
        "hr": "haryana",
        "hp": "himachal pradesh",
        "jh": "jharkhand",
        "ka": "karnataka",
        "kl": "kerala",
        "mh": "maharashtra",
        "mp": "madhya pradesh",
        "ml": "meghalaya",
        "mn": "manipur",
        "mz": "mizoram",
        "nl": "nagaland",
        "od": "odisha",
        "pb": "punjab",
        "rj": "rajasthan",
        "sk": "sikkim",
        "tn": "tamil nadu",
        "ts": "telangana",
        "uk": "uttarakhand",
        "up": "uttar pradesh",
        "wb": "west bengal",
    }

    SPELLING_CORRECTIONS = {
        "banglore": "bangalore",
        "maharastra": "maharashtra",
        "mubmai": "mumbai",
    }

    def normalize_query(self, query: str | None) -> str:
        if not query:
            return ""

        normalized = query.strip().lower()
        normalized = self._PUNCTUATION_PATTERN.sub(" ", normalized)
        normalized = self._WHITESPACE_PATTERN.sub(" ", normalized).strip()
        if not normalized:
            return ""

        tokens = self.normalize_tokens(normalized.split())
        return " ".join(tokens)

    def normalize_tokens(self, tokens: list[str]) -> list[str]:
        normalized_tokens: list[str] = []
        for token in tokens:
            cleaned = token.strip().lower()
            if not cleaned:
                continue
            cleaned = self.SPELLING_CORRECTIONS.get(cleaned, cleaned)
            cleaned = self.ABBREVIATIONS.get(cleaned, cleaned)
            cleaned = self.STATE_ABBREVIATIONS.get(cleaned, cleaned)
            cleaned = cleaned.replace(".", " ")
            normalized_tokens.extend(part for part in cleaned.split() if part)
        return self.remove_duplicate_words(normalized_tokens)

    @staticmethod
    def remove_duplicate_words(tokens: list[str]) -> list[str]:
        seen: set[str] = set()
        deduplicated: list[str] = []
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            deduplicated.append(token)
        return deduplicated
