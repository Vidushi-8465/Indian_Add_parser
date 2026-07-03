"""Build composite full address strings from hierarchical components."""

from __future__ import annotations

import numpy as np
import pandas as pd

_NON_VALUES = {"", "nan", "none", "null", "<na>"}


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
        if not parts:
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

        full_address = pd.Series(result, index=built.index, dtype=object)
        full_address = full_address.mask(full_address == "", pd.NA)
        built["full_address"] = full_address
        return built
