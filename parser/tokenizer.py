"""Query normalization and tokenization helpers."""

from __future__ import annotations

import re


class QueryTokenizer:
    """Normalize address queries and build token / phrase candidates."""

    _PUNCTUATION_PATTERN = re.compile(r"[^\w\s]")
    _WHITESPACE_PATTERN = re.compile(r"\s+")

    ABBREVIATIONS = {
        "apt": "apartment",
        "apt.": "apartment",
        "rd": "road",
        "rd.": "road",
        "st": "street",
        "st.": "street",
        "hno": "house number",
        "h.no": "house number",
        "no": "number",
        "blk": "block",
        "vill": "village",
        "po": "post office",
    }

    SPELLING_CORRECTIONS = {
        "banglore": "bangalore",
        "maharastra": "maharashtra",
        "mubmai": "mumbai",
    }

    STATE_ABBREVIATIONS = {
        "ap": "andhra pradesh",
        "as": "assam",
        "br": "bihar",
        "cg": "chhattisgarh",
        "ch": "chandigarh",
        "dl": "delhi",
        "gj": "gujarat",
        "hr": "haryana",
        "ka": "karnataka",
        "kl": "kerala",
        "mh": "maharashtra",
        "mp": "madhya pradesh",
        "od": "odisha",
        "pb": "punjab",
        "rj": "rajasthan",
        "tn": "tamil nadu",
        "ts": "telangana",
        "up": "uttar pradesh",
        "wb": "west bengal",
    }

    def normalize(self, query: str | None) -> str:
        if not query:
            return ""
        normalized = query.strip().lower()
        normalized = self._PUNCTUATION_PATTERN.sub(" ", normalized)
        normalized = self._WHITESPACE_PATTERN.sub(" ", normalized).strip()
        if not normalized:
            return ""
        return " ".join(self.normalize_tokens(normalized.split()))

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

    @staticmethod
    def tokenize(query: str) -> list[str]:
        return [token for token in query.split() if token]

    @staticmethod
    def generate_phrases(tokens: list[str], max_window: int = 4) -> list[str]:
        phrases: list[str] = []
        if max_window < 2:
            max_window = 2
        for start in range(len(tokens)):
            for end in range(start + 2, min(len(tokens), start + max_window) + 1):
                phrases.append(" ".join(tokens[start:end]))
        return phrases
