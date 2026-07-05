"""Build a combined searchable_text field from key address components."""

from __future__ import annotations

import numpy as np
import pandas as pd

_NON_VALUES = {"", "nan", "none", "null", "<na>"}


class SearchableTextBuilder:
    """Combine searchable fields into one normalized lowercase string."""

    DEFAULT_COMPONENTS = [
        "building_name",
        "road_name",
        "locality",
        "city_name",
        "district_name",
        "subdistrict_name",
        "state_name",
        "pincode",
        "office_name",
    ]

    def build(
        self,
        dataframe: pd.DataFrame,
        components: list[str] | None = None,
        separator: str = " ",
    ) -> pd.DataFrame:
        built = dataframe.copy()
        parts = [column for column in (components or self.DEFAULT_COMPONENTS) if column in built.columns]
        if not parts:
            built["searchable_text"] = pd.NA
            return built

        chunk = built[parts].astype("string")
        for column in parts:
            chunk[column] = chunk[column].str.strip().str.lower()
            chunk[column] = chunk[column].mask(chunk[column].isin(_NON_VALUES))

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

        searchable_text = pd.Series(result, index=built.index, dtype=object)
        searchable_text = searchable_text.str.strip()
        searchable_text = searchable_text.str.replace(r"\s+", " ", regex=True)
        searchable_text = searchable_text.mask(searchable_text == "", pd.NA)
        built["searchable_text"] = searchable_text
        return built
