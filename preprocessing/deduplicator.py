"""Remove duplicate rows from the dataset."""

from __future__ import annotations

import pandas as pd


class Deduplicator:
    """Drop duplicate records while preserving ingestion traceability when configured."""

    def remove_duplicates(
        self,
        dataframe: pd.DataFrame,
        subset_columns: list[str] | None = None,
        keep: str = "first",
    ) -> tuple[pd.DataFrame, int]:
        before = len(dataframe.index)
        dedupe_subset = subset_columns
        if dedupe_subset is None:
            dedupe_subset = [column for column in dataframe.columns if column != "serial_number"]

        deduped = dataframe.drop_duplicates(subset=dedupe_subset, keep=keep).reset_index(drop=True)
        removed = before - len(deduped.index)
        return deduped, removed
