"""Address-level duplicate detection using normalized fingerprints."""

from __future__ import annotations

import pandas as pd

from utils.hash_utils import compute_address_hash
from utils.string_utils import normalize_for_deduplication


class AddressDeduplicator:
    """Detect duplicates such as 'TCS Hinjewadi' vs 'TCS, Hinjewadi'."""

    def add_address_hash(self, dataframe: pd.DataFrame, source_column: str = "full_address") -> pd.DataFrame:
        enriched = dataframe.copy()
        if source_column not in enriched.columns:
            enriched["address_hash"] = pd.NA
            return enriched

        enriched["address_hash"] = enriched[source_column].apply(self._hash_value)
        return enriched

    def remove_address_duplicates(
        self,
        dataframe: pd.DataFrame,
        hash_column: str = "address_hash",
        keep: str = "first",
    ) -> tuple[pd.DataFrame, int]:
        if hash_column not in dataframe.columns:
            return dataframe, 0

        before = len(dataframe.index)
        valid_hashes = self._has_hash(dataframe[hash_column])
        deduped_valid = dataframe.loc[valid_hashes].drop_duplicates(subset=[hash_column], keep=keep)
        without_hash = dataframe.loc[~valid_hashes]
        deduped = pd.concat([deduped_valid, without_hash], ignore_index=True)
        removed = before - len(deduped.index)
        return deduped, removed

    def ensure_unique_hashes(
        self,
        dataframe: pd.DataFrame,
        hash_column: str = "address_hash",
        keep: str = "first",
    ) -> tuple[pd.DataFrame, int]:
        """Final safety pass to guarantee no duplicate address hashes remain."""
        if hash_column not in dataframe.columns:
            return dataframe, 0

        before = len(dataframe.index)
        valid_hashes = self._has_hash(dataframe[hash_column])
        deduped_valid = dataframe.loc[valid_hashes].drop_duplicates(subset=[hash_column], keep=keep)
        without_hash = dataframe.loc[~valid_hashes]
        deduped = pd.concat([deduped_valid, without_hash], ignore_index=True)
        removed = before - len(deduped.index)
        return deduped, removed

    @staticmethod
    def _has_hash(series: pd.Series) -> pd.Series:
        present = series.notna()
        text = series.astype(str).str.strip()
        return present & ~text.str.lower().isin({"", "nan", "none", "null", "na", "n/a", "<na>"})

    @staticmethod
    def _hash_value(value: object) -> object:
        if pd.isna(value):
            return pd.NA
        normalized = normalize_for_deduplication(str(value))
        if not normalized:
            return pd.NA
        return compute_address_hash(normalized)
