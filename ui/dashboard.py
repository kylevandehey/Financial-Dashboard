"""
CORE CASH FLOW — CANONICAL LOGIC

This module defines the single source of truth for income, expense,
and net cash flow calculations across the entire application.

RULES:
- Income = sum(amount > 0)
- Expenses = sum(abs(amount < 0))
- Exclusions are CATEGORY-driven
- transaction_type is intentionally ignored
- Keyword fallback applies if category is missing
- All dashboards, charts, and exports MUST consume this logic

DO NOT:
- Recalculate income/expenses elsewhere
- Use transaction_type for exclusion logic
- Bypass this module for UI metrics

Any changes here require explicit audit validation.
"""

import streamlit as st
import pandas as pd
from datetime import date

from src.formatting import format_currency, format_date_range


def _coerce_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    return pd.DataFrame(df).copy()


def _filter_by_year(df: pd.DataFrame, year_label: str) -> pd.DataFrame:
    if df.empty or year_label == "ALL YEARS":
        return df
    if "date" not in df.columns:
        return df
    try:
        year = int(year_label)
    except ValueError:
        return df
    dates = pd.to_datetime(df["date"], errors="coerce")
    return df.loc[dates.dt.year == year]


def _derive_date_range(df: pd.DataFrame) -> tuple[date, date] | None:
    if df.empty or "date" not in df.columns:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return dates.min().date(), dates.max().date()


def _norm(val: object) -> str:
    return " ".join(str(val or "").lower().replace("_", " ").replace("-", " ").split())


def _build_exclusion_mask(df: pd.DataFrame) -> pd.Series:
    """
    Monarch-authoritative exclusion:
    - Use Category column FIRST
    - Ignore transaction_type entirely
    """
    if df.empty:
        return pd.Series(False, index=df.index)

    excluded_categories = {
        "transfer",
        "credit card payment",
        "refund",
    }

    if "category" in df.columns:
        cat_norm = df["category"].apply(_norm)
        return cat_norm.isin(excluded_categories)

    # Fallback: keyword scan
    scan_cols = [c for c in ["merchant", "notes", "original_statement"] if c in df.columns]
    if scan_cols:
        haystack = (
            df[scan_cols]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .apply(_norm)
        )
        return haystack.apply(
            lambda txt: any(x in txt for x in excluded_categories)
        )

    return pd.Series(False, index=df.index)


def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
) -> None:
    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    year_tabs = st.tabs(available_years)

    for tab, year_label in zip(year_tabs, available_years):
        with tab:
            scoped_tx = _filter_by_year(_coerce_df(transactions), year_label)
            derived_range = _derive_date_range(scoped_tx)

            st.caption(f"Scope: {year_label}")
            if derived_range:
                st.caption("Date Range")
                st.caption(format_date_range(derived_range))

            if scoped_tx.empty or "amount" not in scoped_tx.columns:
                st.info("No transactions in scope.")
                continue

            amounts = pd.to_numeric(scoped_tx["amount"], errors="coerce").fillna(0.0)

            exclusion_mask = _build_exclusion_mask(scoped_tx)
            included = amounts.loc[~exclusion_mask]

            income = float(included[included > 0].sum())
            expenses = float((-included[included < 0]).sum())
            net = float(income - expenses)

            st.markdown("### Key Metrics (Core Cash Flow v1)")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Income", format_currency(income))
            with c2:
                st.metric("Expenses", format_currency(expenses))
            with c3:
                st.metric("Net", format_currency(net))

            # ---- Audit ----
            st.caption(
                f"Audit: Included rows = {(~exclusion_mask).sum()} | "
                f"Excluded rows = {exclusion_mask.sum()} | "
                f"Category-driven exclusions"
            )

            with st.expander("Show excluded rows (audit)", expanded=False):
                cols = [c for c in ["date", "merchant", "category", "amount"] if c in scoped_tx.columns]
                st.dataframe(scoped_tx.loc[exclusion_mask, cols], use_container_width=True)
