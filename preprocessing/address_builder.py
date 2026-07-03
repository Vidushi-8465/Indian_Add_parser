"""Build composite full address strings from hierarchical components."""

from __future__ import annotations

import pandas as pd


class AddressBuilder:
    """Construct full_address from building through pincode."""

    DEFAULT_COMPONENTS = [
        "building_name",
        "road_name",
        "locality",
        "city_name",
        "district_name",
        "state_name",
        "pincode",
    ]

    def build(
        self,
        dataframe: pd.DataFrame,
        components: list[str] | None = None,
        separator: str = ", ",
    ) -> pd.DataFrame:
        built = dataframe.copy()
        parts = [column for column in (components or self.DEFAULT_COMPONENTS) if column in built.columns]
        built["full_address"] = built.apply(
            lambda row: self._compose_row(row, parts, separator),
            axis=1,
        )
        return built

    @staticmethod
    def _compose_row(row: pd.Series, components: list[str], separator: str) -> object:
        values: list[str] = []
        for column in components:
            value = row.get(column)
            if pd.isna(value):
                continue
            text = str(value).strip()
            if text and text.lower() not in {"nan", "none", "null"}:
                values.append(text)
        if not values:
            return pd.NA
        return separator.join(values)
