"""
Streamlit rendering helpers for category metric cards.
"""

from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd
import streamlit as st

from src.categories import format_accounting_currency, get_all_categories, get_top_categories


def _chunk_dataframe(df: pd.DataFrame, size: int) -> Iterable[pd.DataFrame]:
    for start in range(0, len(df), size):
        yield df.iloc[start : start + size]


def render_category_metric_cards(
    category_totals: pd.DataFrame,
    *,
    show_all: bool = False,
    top_n: int = 5,
    icon: Optional[str] = "📊",
    columns: int = 3,
    empty_message: str = "No categories to display.",
) -> None:
    """
    Render st.metric()-style cards for category totals.

    The caller controls whether to show top N or the full list via the
    `show_all` flag. No Streamlit state is managed inside this helper.
    """
    if category_totals is None or category_totals.empty:
        st.info(empty_message)
        return

    ordered = get_all_categories(category_totals) if show_all else get_top_categories(category_totals, n=top_n)

    if ordered.empty:
        st.info(empty_message)
        return

    for chunk in _chunk_dataframe(ordered, columns):
        cols = st.columns(len(chunk))
        for col, (_, row) in zip(cols, chunk.iterrows()):
            label_prefix = f"{icon} " if icon else ""
            label = f"{label_prefix}{row['category']}"
            value = format_accounting_currency(row["total_amount"])
            delta = f"{int(row['transaction_count'])} tx"
            col.metric(label=label, value=value, delta=delta)
