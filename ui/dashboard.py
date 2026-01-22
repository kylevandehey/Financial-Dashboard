# ui/dashboard.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from src.cash_flow import compute_cash_flow, build_exclusion_mask
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


# =====================================================
# Defaults (ONLY THESE TWO)
# =====================================================
DEFAULT_EXCLUDE_EXACT = {
    "transfer",
    "credit card payment",
}


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
    tx = _ensure_datetime(_coerce_df(tx))
    if tx.empty:
        return "empty"
    return f"{len(tx)}|{tx['date'].min()}|{tx['date'].max()}|{tx['amount'].sum():.2f}"


def _infer_default_excludes(categories: List[str]) -> List[str]:
    out = []
    for c in categories:
        if str(c).strip().lower() in DEFAULT_EXCLUDE_EXACT:
            out.append(c)
    return sorted(set(out), key=lambda x: x.lower())


def _init_exclusion_state_if_needed(tx: pd.DataFrame) -> None:
    sig = _dataset_signature(tx)

    if st.session_state.get(_SS_DATASET_SIG) != sig:
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

        if _SS_PRESET not in st.session_state:
            st.session_state[_SS_PRESET] = "ALL YEARS"


def _derive_full_range(tx: pd.DataFrame) -> Tuple[date, date]:
    return tx["date"].min().date(), tx["date"].max().date()


def _available_years(tx: pd.DataFrame) -> List[int]:
    return sorted(tx["date"].dt.year.unique().tolist())


def _filter_by_date(tx: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    mask = (tx["date"].dt.date >= start) & (tx["date"].dt.date <= end)
    return tx.loc[mask].copy()


# =====================================================
# Date Controls
# =====================================================
@dataclass
class DateControlResult:
    filtered_tx: pd.DataFrame
    start_date: date
    end_date: date
    label: str


def _render_date_controls(tx: pd.DataFrame) -> DateControlResult:
    data_min, data_max = _derive_full_range(tx)
    years = _available_years(tx)

    presets = (
        ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 180 Days", "Last Full Year"]
        + ["ALL YEARS"]
        + [str(y) for y in years]
        + ["Custom Range"]
    )

    st.markdown("### Date Range Presets")

    preset = st.selectbox(
        "Date Range Presets",
        presets,
        index=presets.index(st.session_state.get(_SS_PRESET, "ALL YEARS")),
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

    return DateControlResult(
        filtered_tx=_filter_by_date(tx, start, end),
        start_date=start,
        end_date=end,
        label=preset,
    )


# =====================================================
# UI
# =====================================================
def render_dashboard_tab(transactions: pd.DataFrame) -> None:
    tx = _ensure_datetime(_coerce_df(transactions))
    _init_exclusion_state_if_needed(tx)

    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    dc = _render_date_controls(tx)
    scoped_tx = dc.filtered_tx

    result = compute_cash_flow(scoped_tx)

    st.markdown("## Snapshot")
    c1, c2, c3 = st.columns(3)
    c1.metric("Income", format_currency(result.income))
    c2.metric("Expenses", format_currency(result.net_expenses))
    c3.metric("Net Cash Flow", format_currency(result.net_cash))

    st.markdown("## Snapshot Details")

    categories = (
        scoped_tx.get("category", pd.Series(dtype=str))
        .fillna("")
        .astype(str)
        .unique()
        .tolist()
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.multiselect(
            "Exclude categories (Income)",
            categories,
            key=_SS_EXCL_INCOME,
        )
    with c2:
        st.multiselect(
            "Exclude categories (Expenses)",
            categories,
            key=_SS_EXCL_EXPENSE,
        )
    with c3:
        st.multiselect(
            "Exclude categories (Frequency)",
            categories,
            key=_SS_EXCL_FREQ,
        )

    st.caption("Exclusions persist across date ranges until manually cleared.")
