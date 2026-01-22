# ui/dashboard.py

import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, timedelta

from src.cash_flow import compute_cash_flow
from src.formatting import format_currency, format_date_range


# =====================================================
# Constants / Session Keys
# =====================================================

_SS_PRESET = "dashboard_date_preset"
_SS_START = "dashboard_start_date"
_SS_END = "dashboard_end_date"


# =====================================================
# Date Preset Logic (Ledger-Style)
# =====================================================

def _get_available_years(tx: pd.DataFrame) -> list[str]:
    if tx.empty or "date" not in tx.columns:
        return []

    years = (
        pd.to_datetime(tx["date"], errors="coerce")
        .dropna()
        .dt.year
        .astype(int)
        .unique()
        .tolist()
    )
    return sorted(years, reverse=True)


def _resolve_preset(preset: str, tx: pd.DataFrame):
    today = date.today()

    if preset == "Last 7 Days":
        return today - timedelta(days=6), today
    if preset == "Last 30 Days":
        return today - timedelta(days=29), today
    if preset == "Last 90 Days":
        return today - timedelta(days=89), today
    if preset == "Last 180 Days":
        return today - timedelta(days=179), today
    if preset == "Last Full Year":
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)

    # Year selections
    if preset.isdigit():
        y = int(preset)
        return date(y, 1, 1), date(y, 12, 31)

    # ALL YEARS
    if preset == "ALL YEARS":
        dates = pd.to_datetime(tx["date"], errors="coerce").dropna()
        if dates.empty:
            return None, None
        return dates.min().date(), dates.max().date()

    return None, None


def _render_date_controls(tx: pd.DataFrame):
    years = _get_available_years(tx)

    preset_options = (
        [
            "Last 7 Days",
            "Last 30 Days",
            "Last 90 Days",
            "Last 180 Days",
            "Last Full Year",
        ]
        + [str(y) for y in years]
        + ["ALL YEARS", "Custom Range"]
    )

    if _SS_PRESET not in st.session_state:
        st.session_state[_SS_PRESET] = "ALL YEARS"

    st.markdown("### Date Range Presets")

    preset = st.selectbox(
        "Date Range Presets",
        preset_options,
        index=preset_options.index(st.session_state[_SS_PRESET]),
    )

    st.session_state[_SS_PRESET] = preset

    if preset == "Custom Range":
        c1, c2 = st.columns(2)

        with c1:
            start = st.date_input(
                "Start Date",
                value=st.session_state.get(_SS_START),
                key=_SS_START,
            )
        with c2:
            end = st.date_input(
                "End Date",
                value=st.session_state.get(_SS_END),
                key=_SS_END,
            )
    else:
        start, end = _resolve_preset(preset, tx)
        st.session_state[_SS_START] = start
        st.session_state[_SS_END] = end

    return st.session_state[_SS_START], st.session_state[_SS_END]


# =====================================================
# Filtering
# =====================================================

def _apply_date_filter(tx: pd.DataFrame, start, end):
    if tx.empty or not start or not end:
        return tx

    df = tx.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.loc[
        (df["date"].dt.date >= start)
        & (df["date"].dt.date <= end)
    ]


# =====================================================
# Snapshot Helpers
# =====================================================

def _snapshot_metrics(tx: pd.DataFrame):
    r = compute_cash_flow(tx)
    return r.income, r.net_expenses, r.net_cash


def _top_income_categories(tx: pd.DataFrame, excluded: list[str]):
    df = tx[~tx["category"].isin(excluded)]
    inc = df[df["amount"] > 0]
    out = (
        inc.groupby("category", dropna=False)["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .reset_index()
    )
    out["amount_fmt"] = out["amount"].apply(format_currency)
    return out


def _top_expense_categories(tx: pd.DataFrame, excluded: list[str]):
    df = tx[~tx["category"].isin(excluded)]
    exp = df[df["amount"] < 0]
    out = (
        exp.groupby("category", dropna=False)["amount"]
        .sum()
        .sort_values()
        .head(5)
        .reset_index()
    )
    out["amount_fmt"] = out["amount"].apply(format_currency)
    return out


def _most_frequent_expenses(tx: pd.DataFrame, excluded: list[str]):
    df = tx[(tx["amount"] < 0) & (~tx["category"].isin(excluded))]
    agg = (
        df.groupby("category", dropna=False)["amount"]
        .agg(
            occurrences="count",
            total_spend="sum",
            avg_spend="mean",
        )
        .reset_index()
        .sort_values("occurrences", ascending=False)
        .head(5)
    )

    agg["total_fmt"] = agg["total_spend"].apply(format_currency)
    agg["avg_fmt"] = agg["avg_spend"].apply(format_currency)
    return agg


# =====================================================
# Charts
# =====================================================

def _bar_chart(df, x, y, title, tooltip):
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(x, sort="-y"),
            y=alt.Y(y),
            tooltip=tooltip,
        )
        .properties(height=280, title=title)
    )


# =====================================================
# Main Render
# =====================================================

def render_dashboard_tab(transactions: pd.DataFrame):
    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    start, end = _render_date_controls(transactions)

    if start and end:
        st.caption("Date Range")
        st.caption(format_date_range((start, end)))

    tx = _apply_date_filter(transactions, start, end)

    if tx.empty:
        st.info("No transactions in selected range.")
        return

    # -------------------------------------------------
    # Snapshot
    # -------------------------------------------------

    income, expenses, net = _snapshot_metrics(tx)

    st.markdown("## Snapshot")

    c1, c2, c3 = st.columns(3)
    c1.metric("Income", format_currency(income))
    c2.metric("Expenses", format_currency(expenses))
    c3.metric("Net Cash Flow", format_currency(net))

    # -------------------------------------------------
    # Exclusions
    # -------------------------------------------------

    st.markdown("## Snapshot Details")

    all_categories = sorted(tx["category"].dropna().unique().tolist())

    excluded = st.multiselect(
        "Exclude categories from charts",
        all_categories,
        default=[],
    )

    # -------------------------------------------------
    # Charts
    # -------------------------------------------------

    i1, i2, i3 = st.columns(3)

    with i1:
        st.markdown("### Top Income Sources")
        inc = _top_income_categories(tx, excluded)
        if not inc.empty:
            st.altair_chart(
                _bar_chart(
                    inc,
                    "category:N",
                    "amount:Q",
                    "Top Income",
                    [
                        alt.Tooltip("category:N"),
                        alt.Tooltip("amount_fmt:N", title="Total"),
                    ],
                ),
                use_container_width=True,
            )

    with i2:
        st.markdown("### Top Expenses")
        exp = _top_expense_categories(tx, excluded)
        if not exp.empty:
            st.altair_chart(
                _bar_chart(
                    exp,
                    "category:N",
                    "amount:Q",
                    "Top Expenses",
                    [
                        alt.Tooltip("category:N"),
                        alt.Tooltip("amount_fmt:N", title="Total"),
                    ],
                ),
                use_container_width=True,
            )

    with i3:
        st.markdown("### Most Frequent Expenses")
        freq = _most_frequent_expenses(tx, excluded)
        if not freq.empty:
            st.altair_chart(
                _bar_chart(
                    freq,
                    "category:N",
                    "occurrences:Q",
                    "Frequency",
                    [
                        alt.Tooltip("category:N"),
                        alt.Tooltip("occurrences:Q", title="Count"),
                        alt.Tooltip("total_fmt:N", title="Total Spend"),
                        alt.Tooltip("avg_fmt:N", title="Avg Spend"),
                    ],
                ),
                use_container_width=True,
            )

