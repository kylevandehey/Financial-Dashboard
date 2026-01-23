# ui/dashboard.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from src.cash_flow import compute_cash_flow
from src.formatting import format_currency, format_date_range


# =====================================================
# Session State Keys
# =====================================================
_SS_DATASET_SIG = "dash_dataset_signature_v2"

_SS_PRESET = "dash_date_preset_v2"
_SS_CUSTOM_START = "dash_custom_start_v2"
_SS_CUSTOM_END = "dash_custom_end_v2"

_SS_EXCL_INCOME = "dash_exclude_income_categories_v2"
_SS_EXCL_EXPENSE = "dash_exclude_expense_categories_v2"
_SS_EXCL_FREQ = "dash_exclude_frequency_categories_v2"


DEFAULT_EXCLUDE_EXACT = {"transfer", "credit card payment"}


# =====================================================
# Helpers
# =====================================================
def _coerce_df(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    return pd.DataFrame(df).copy() if df is not None else pd.DataFrame()


def _ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if "date" in df.columns:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
    return df


def _dataset_signature(tx: pd.DataFrame) -> str:
    if tx.empty:
        return "empty"
    return f"{len(tx)}|{tx['date'].min()}|{tx['date'].max()}|{tx['amount'].sum():.2f}"


def _infer_default_excludes(categories: List[str]) -> List[str]:
    return sorted(
        [c for c in categories if c.lower().strip() in DEFAULT_EXCLUDE_EXACT],
        key=str.lower,
    )


def _init_exclusion_state(tx: pd.DataFrame) -> None:
    sig = _dataset_signature(tx)
    if st.session_state.get(_SS_DATASET_SIG) == sig:
        return

    cats = (
        tx.get("category", pd.Series(dtype=str))
        .fillna("")
        .astype(str)
        .unique()
        .tolist()
    )

    defaults = _infer_default_excludes(cats)

    st.session_state[_SS_DATASET_SIG] = sig
    st.session_state[_SS_EXCL_INCOME] = defaults.copy()
    st.session_state[_SS_EXCL_EXPENSE] = defaults.copy()
    st.session_state[_SS_EXCL_FREQ] = defaults.copy()
    st.session_state.setdefault(_SS_PRESET, "ALL YEARS")


# =====================================================
# Date Controls
# =====================================================
@dataclass
class DateControlResult:
    tx: pd.DataFrame
    start: date
    end: date


def _render_date_controls(tx: pd.DataFrame) -> DateControlResult:
    data_min, data_max = tx["date"].min().date(), tx["date"].max().date()
    years = sorted(tx["date"].dt.year.unique().tolist())

    presets = (
        ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 180 Days", "Last Full Year"]
        + ["ALL YEARS"]
        + [str(y) for y in years]
        + ["Custom Range"]
    )

    preset = st.selectbox(
        "Date Range Presets",
        presets,
        key=_SS_PRESET,
    )

    today = datetime.now().date()

    if preset == "Last 7 Days":
        start, end = today - timedelta(days=6), today
    elif preset == "Last 30 Days":
        start, end = today - timedelta(days=29), today
    elif preset == "Last 90 Days":
        start, end = today - timedelta(days=89), today
    elif preset == "Last 180 Days":
        start, end = today - timedelta(days=179), today
    elif preset == "Last Full Year":
        y = today.year - 1
        start, end = date(y, 1, 1), date(y, 12, 31)
    elif preset == "Custom Range":
        start = st.date_input("Start date", st.session_state.get(_SS_CUSTOM_START, data_min))
        end = st.date_input("End date", st.session_state.get(_SS_CUSTOM_END, data_max))
        st.session_state[_SS_CUSTOM_START] = start
        st.session_state[_SS_CUSTOM_END] = end
    elif preset == "ALL YEARS":
        start, end = data_min, data_max
    else:
        y = int(preset)
        start, end = date(y, 1, 1), date(y, 12, 31)

    start = max(start, data_min)
    end = min(end, data_max)

    st.caption("Date Range")
    st.caption(format_date_range((start, end)))

    mask = (tx["date"].dt.date >= start) & (tx["date"].dt.date <= end)
    return DateControlResult(tx=tx.loc[mask].copy(), start=start, end=end)


# =====================================================
# Dashboard
# =====================================================
def render_dashboard_tab(transactions: pd.DataFrame) -> None:
    tx = _ensure_datetime(_coerce_df(transactions))
    _init_exclusion_state(tx)

    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    dc = _render_date_controls(tx)
    scoped = dc.tx

    result = compute_cash_flow(scoped)

    # ---------------- Snapshot ----------------
    st.markdown("## Snapshot")
    c1, c2, c3 = st.columns(3)
    c1.metric("Income", format_currency(result.income))
    c2.metric("Expenses", format_currency(result.net_expenses))
    c3.metric("Net Cash Flow", format_currency(result.net_cash))

    # ---------------- Exclusions ----------------
    st.markdown("## Snapshot Details")

    categories = sorted(
        scoped["category"].fillna("").astype(str).unique().tolist(),
        key=str.lower,
    )

    c1, c2, c3 = st.columns(3)
    c1.multiselect("Exclude categories (Income)", categories, key=_SS_EXCL_INCOME)
    c2.multiselect("Exclude categories (Expenses)", categories, key=_SS_EXCL_EXPENSE)
    c3.multiselect("Exclude categories (Frequency)", categories, key=_SS_EXCL_FREQ)

    # ---------------- Charts ----------------
    def _bar_chart(df, x, y, title, tooltip):
        return (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(x, sort="-y"),
                y=y,
                tooltip=tooltip,
            )
            .properties(title=title, height=300)
        )

    # Income
    income_df = (
        scoped[
            (scoped["amount"] > 0)
            & ~scoped["category"].isin(st.session_state[_SS_EXCL_INCOME])
        ]
        .groupby("category")["amount"]
        .sum()
        .nlargest(10)
        .reset_index()
    )
    income_df["fmt"] = income_df["amount"].apply(format_currency)

    # Expenses
    expense_df = (
        scoped[
            (scoped["amount"] < 0)
            & ~scoped["category"].isin(st.session_state[_SS_EXCL_EXPENSE])
        ]
        .groupby("category")["amount"]
        .sum()
        .abs()
        .nlargest(10)
        .reset_index()
    )
    expense_df["fmt"] = expense_df["amount"].apply(format_currency)

    # Frequency
    freq_df = (
        scoped[
            (scoped["amount"] < 0)
            & ~scoped["category"].isin(st.session_state[_SS_EXCL_FREQ])
        ]
        .groupby("category")
        .agg(
            occurrences=("amount", "count"),
            total=("amount", lambda s: abs(s.sum())),
        )
        .nlargest(10, "occurrences")
        .reset_index()
    )
    freq_df["total_fmt"] = freq_df["total"].apply(format_currency)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.altair_chart(
            _bar_chart(
                income_df,
                "category:N",
                "amount:Q",
                "Top Income Sources",
                ["category", "fmt"],
            ),
            use_container_width=True,
        )

    with c2:
        st.altair_chart(
            _bar_chart(
                expense_df,
                "category:N",
                "amount:Q",
                "Top Expenses",
                ["category", "fmt"],
            ),
            use_container_width=True,
        )

    with c3:
        st.altair_chart(
            _bar_chart(
                freq_df,
                "category:N",
                "occurrences:Q",
                "Most Frequent Expenses",
                ["category", "occurrences", "total_fmt"],
            ),
            use_container_width=True,
        )
