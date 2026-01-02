"""Formatting helpers for Control Tower dashboards.

This module centralizes currency formatting so all UI surfaces use the same
accounting-style convention (negative values in parentheses, no negative sign).
"""

from __future__ import annotations

import pandas as pd


def format_currency(value: float) -> str:
    """Return a single value formatted as currency with accounting negatives.

    Negative values are wrapped in parentheses instead of a leading minus sign.
    This function is intentionally lightweight so it can be reused in vectorized
    pandas operations via :func:`format_currency_series`.
    """

    if pd.isna(value):
        return ""

    amount = float(value)
    formatted = f"${abs(amount):,.2f}"
    return f"({formatted})" if amount < 0 else formatted


def format_currency_series(amounts: pd.Series) -> pd.Series:
    """Vectorized currency formatter with accounting-style negatives.

    Args:
        amounts: Numeric pandas Series to format.

    Returns:
        pandas Series of formatted currency strings, preserving the original
        index to avoid downstream alignment issues.
    """

    numeric_amounts = pd.to_numeric(amounts, errors="coerce")
    formatted = numeric_amounts.abs().map(lambda x: f"${x:,.2f}")
    negatives = numeric_amounts < 0
    formatted.loc[negatives] = formatted.loc[negatives].map(lambda x: f"({x})")
    formatted.loc[numeric_amounts.isna()] = ""
    return formatted
