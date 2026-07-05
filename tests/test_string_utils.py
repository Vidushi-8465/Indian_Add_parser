"""Tests for shared string utilities."""

from __future__ import annotations

import pandas as pd

from utils.string_utils import coerce_identifier_string


def test_coerce_identifier_string_strips_float_suffix() -> None:
    assert coerce_identifier_string(411057.0) == "411057"
    assert coerce_identifier_string("411057.0") == "411057"
    assert coerce_identifier_string(27) == "27"
    assert coerce_identifier_string("603.0") == "603"
    assert pd.isna(coerce_identifier_string(None))
    assert pd.isna(coerce_identifier_string(""))
