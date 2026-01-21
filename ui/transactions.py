"""
Transactions Tab (Core Rebuild)

Goal
- Provide stable transaction browsing
- Add year tabs here (ALL YEARS + each year present in the CSV)
- Do NOT implement cash flow logic here (canonical logic lives in src.cash_flow)
"""

from __future__ import annotations

from datetime import date as date_cls
import pandas as pd
import streamlit as st


_ALL_YEARS_LABEL = "ALL YEARS"


def _coerce_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    return pd.DataFrame(df).copy()


def _available_year_labels(df: pd.DataFrame) -> list[str]:
    if df.empty or "date" not in df.columns:
        return [_ALL_YEARS_LABEL]

    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return [_ALL_YEARS_LABEL]

    years = sorted(dates.dt.year.astype(int).unique().tolist(), reverse=True)
    return [_ALL_YEARS_LABEL] + [str(y) for y in years]


def _filter_by_year(df: pd.DataFrame, year_label: str) -> pd.DataFrame:
    if df.empty or year_label == _ALL_YEARS_LABEL or "date" not in df.columns:
        return df

    try:
        year = int(year_label)
    except ValueError:
        return df

    dates = pd.to_datetime(df["date"], errors="coerce")
    return df.loc[dates.dt.year == year]


def render_transactions_tab(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame | None = None,  # reserved for later
    *,
    year_labels: list[str] | None = None,
) -> None:
    st.markdown("## Transactions (Core Rebuild)")
    tx = _coerce_df(transactions)

    if tx.empty:
        st.info("Upload Monarch CSVs to view transactions.")
        return

    # Year tabs belong here (not Dashboard)
    labels = year_labels or _available_year_labels(tx)
    tabs = st.tabs(labels)

    # Clean display column ordering (only show what exists)
    preferred_cols = [
        "date",
        "merchant",
        "category",
        "account",
        "amount",
        "transaction_type",
        "notes",
    ]
    display_cols = [c for c in preferred_cols if c in tx.columns]
    fallback_cols = [c for c in tx.columns if c not in display_cols]
    cols = display_cols + fallback_cols

    for tab, label in zip(tabs, labels):
        with tab:
            scoped = _filter_by_year(tx, label)
            st.caption(f"Rows: {len(scoped):,}")
            st.dataframe(scoped[cols], use_container_width=True, hide_index=True)
