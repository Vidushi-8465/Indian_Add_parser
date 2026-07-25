"""Build composite full address strings from hierarchical components."""

from __future__ import annotations

import numpy as np
import pandas as pd

_NON_VALUES = {"", "nan", "none", "null", "<na>"}


class AddressBuilder:
    """Construct full_address from building through pincode."""

    DEFAULT_COMPONENTS = [
        "building_number",
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
        existing = self._normalized_series(built["full_address"]) if "full_address" in built.columns else None

        parts = [column for column in (components or self.DEFAULT_COMPONENTS) if column in built.columns]
        if not parts:
            if existing is None:
                built["full_address"] = pd.NA
            return built

        chunk = built[parts].astype("string")
        for column in parts:
            chunk[column] = chunk[column].str.strip()
            chunk[column] = chunk[column].mask(chunk[column].str.lower().isin(_NON_VALUES))

        arrays = [chunk[column].fillna("").to_numpy(dtype=object) for column in parts]
        result = arrays[0]
        for array in arrays[1:]:
            both = (result != "") & (array != "")
            only_right = (result == "") & (array != "")
            result = np.where(
                both,
                result + separator + array,
                np.where(only_right, array, result),
            )

        composed = pd.Series(result, index=built.index, dtype=object)
        composed = composed.mask(composed == "", pd.NA)

        # Keep rich source addresses (e.g. bldg_address) when present.
        if existing is not None:
            built["full_address"] = existing.where(existing.notna(), composed)
        else:
            built["full_address"] = composed
        return built

    @staticmethod
    def _normalized_series(series: pd.Series) -> pd.Series:
        values = series.astype("string").str.strip()
        return values.mask(values.str.lower().isin(_NON_VALUES) | values.isna())
