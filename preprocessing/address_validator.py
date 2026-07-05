"""Filter rows that do not meet minimum address quality rules."""

from __future__ import annotations

from typing import Any

import pandas as pd


class AddressValidator:
    """Remove invalid addresses from the final dataset."""

    _NULL_LIKE = {"", "nan", "none", "null", "na", "n/a", "<na>"}

    def filter_invalid_addresses(
        self,
        dataframe: pd.DataFrame,
        rules: dict[str, Any] | None = None,
    ) -> tuple[pd.DataFrame, int]:
        rules = rules or {}
        if dataframe.empty:
            return dataframe, 0

        invalid_mask = self.build_invalid_mask(dataframe, rules)
        removed = int(invalid_mask.sum())
        if removed == 0:
            return dataframe, 0
        return dataframe.loc[~invalid_mask].reset_index(drop=True), removed

    def build_invalid_mask(self, dataframe: pd.DataFrame, rules: dict[str, Any]) -> pd.Series:
        invalid = pd.Series(False, index=dataframe.index)

        if rules.get("require_full_address", True) and "full_address" in dataframe.columns:
            invalid |= ~self._field_present(dataframe["full_address"])

        if rules.get("require_address_hash", True) and "address_hash" in dataframe.columns:
            invalid |= ~self._field_present(dataframe["address_hash"])

        location_fields = rules.get(
            "location_fields",
            ["locality", "city_name", "district_name", "state_name", "pincode"],
        )
        min_location_fields = int(rules.get("min_location_fields", 2))
        present_count = pd.Series(0, index=dataframe.index)
        for field in location_fields:
            if field in dataframe.columns:
                present_count += self._field_present(dataframe[field]).astype(int)
        invalid |= present_count < min_location_fields

        min_quality_score = rules.get("min_quality_score")
        if min_quality_score is not None and "quality_score" in dataframe.columns:
            scores = pd.to_numeric(dataframe["quality_score"], errors="coerce")
            invalid |= scores.isna() | (scores < float(min_quality_score))

        if rules.get("require_pincode_or_coordinates", False):
            invalid |= ~self._has_valid_pincode_or_coordinates(dataframe)

        return invalid

    def _has_valid_pincode_or_coordinates(self, dataframe: pd.DataFrame) -> pd.Series:
        has_pincode = pd.Series(False, index=dataframe.index)
        if "pincode" in dataframe.columns:
            has_pincode = self._field_present(dataframe["pincode"])

        has_coordinates = pd.Series(False, index=dataframe.index)
        if "latitude" in dataframe.columns and "longitude" in dataframe.columns:
            lat_present = self._field_present(dataframe["latitude"])
            lon_present = self._field_present(dataframe["longitude"])
            has_coordinates = lat_present & lon_present

        return has_pincode | has_coordinates

    def _field_present(self, series: pd.Series) -> pd.Series:
        present = series.notna()
        text = series.astype(str).str.strip()
        return present & ~text.str.lower().isin(self._NULL_LIKE) & (text != "")
