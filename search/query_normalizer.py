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
        "apts": "apartment",
        "appt": "apartment",
        "ave": "avenue",
        "blk": "block",
        "blk.": "block",
        "bldg": "building",
        "bldg.": "building",
        "col": "colony",
        "cir": "circle",
        "dist": "district",
        "dist.": "district",
        "distt": "district",
        "extn": "extension",
        "ext": "extension",
        "gpo": "general post office",
        "hno": "house number",
        "h.no": "house number",
        "hwy": "highway",
        "ln": "lane",
        "marg": "marg",
        "nr": "near",
        "ofc": "office",
        "opp": "opposite",
        "po": "post office",
        "p.o": "post office",
        "ps": "police station",
        "rd": "road",
        "rd.": "road",
        "sec": "sector",
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
        # Cities
        "banglore": "bangalore",
        "bangaluru": "bengaluru",
        "bengalore": "bangalore",
        "mubmai": "mumbai",
        "mumbay": "mumbai",
        "bombay": "mumbai",
        "dilli": "delhi",
        "dehli": "delhi",
        "delih": "delhi",
        "kolkatta": "kolkata",
        "calcutta": "kolkata",
        "chennnai": "chennai",
        "chenai": "chennai",
        "madras": "chennai",
        "hydrabad": "hyderabad",
        "hyderbad": "hyderabad",
        "pune": "pune",
        "puna": "pune",
        "poona": "pune",
        "ahmadabad": "ahmedabad",
        "ahemdabad": "ahmedabad",
        "gurgaon": "gurugram",
        "noida": "noida",
        "jaipur": "jaipur",
        "jaypur": "jaipur",
        "lucknow": "lucknow",
        "lucknao": "lucknow",
        "kochi": "kochi",
        "cochin": "kochi",
        # States
        "maharastra": "maharashtra",
        "maharasthra": "maharashtra",
        "karnatka": "karnataka",
        "karnataka": "karnataka",
        "tamilnadu": "tamil nadu",
        "gujrat": "gujarat",
        "rajastan": "rajasthan",
        "rajasthaan": "rajasthan",
        "punjaab": "punjab",
        "harayana": "haryana",
        "utterpradesh": "uttar pradesh",
        "westbengal": "west bengal",
        "telengana": "telangana",
        # Common address words
        "nagur": "nagar",
        "raod": "road",
        "rood": "road",
        "strt": "street",
        "steet": "street",
        "colny": "colony",
        "socity": "society",
        "soceity": "society",
        "appartment": "apartment",
        "apartement": "apartment",
        "bulding": "building",
        "buliding": "building",
        "neer": "near",
        "oppsite": "opposite",
        "oposite": "opposite",
        "sekter": "sector",
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

    @staticmethod
    def extract_numbers(query: str | None) -> list[str]:
        """Return all numeric tokens (house/flat numbers, pincodes, etc.)."""
        if not query:
            return []
        return re.findall(r"\d+", query)

    @classmethod
    def has_potential_pincode(cls, query: str | None) -> bool:
        """True when the query contains a six-digit sequence."""
        return any(len(number) == 6 for number in cls.extract_numbers(query))
