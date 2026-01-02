"""Streamlit dashboard tab with defensive rendering and YoY analytics."""

from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL
from src.metrics import (
    build_category_breakdown,
    build_monthly_cash_flow,
    build_yearly_balance_trends,
    build_yearly_income_expense,
    summarize_cash_flow,
)

_QUARTER_MONTHS: dict[str, set[int]] = {
    "Q1": {1, 2, 3},
    "Q2": {4, 5, 6},
    "Q3": {7, 8, 9},
    "Q4": {10, 11, 12},
}


def _coerce_dataframe(data: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Return a copy of the incoming data or an empty frame."""
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def _format_currency(value: float) -> str:
    """Format currency using accounting style for negatives."""
    amount = float(value or 0)
    formatted = f"${abs(amount):,.2f}"
    return f"({formatted})" if amount < 0 else formatted


def _render_header(year_label: str, selected_period: str, date_range: tuple[date, date]) -> None:
    """Render the dashboard heading and scope context."""
    start_date, end_date = date_range
    st.markdown("### Dashboard Overview")
    st.caption(
        f"Scope: {year_label} · Period: {selected_period} · "
        f"{start_date.strftime('%b %d, %Y')} → {end_date.strftime('%b %d, %Y')}"
    )


def render_key_metrics(transactions: pd.DataFrame) -> None:
    """Render headline metrics with accounting-style formatting and guards."""
    if transactions is None or transactions.empty:
        st.info("No data available for selected filters.")
        return

    st.markdown("#### Key Metrics")
    totals = summarize_cash_flow(transactions)
    st.metric("Transactions", f"{len(transactions.index):,}")
    st.metric("Income", _format_currency(totals.income))
    st.metric("Expenses", _format_currency(totals.expenses))
    st.metric("Net Cash Flow", _format_currency(totals.net))


def render_monthly_cash_flow(transactions: pd.DataFrame, date_range: tuple[date, date]) -> None:
    if transactions is None or transactions.empty:
        st.info("No data available for selected filters.")
        return

    st.markdown("#### Cash Flow")
    monthly = build_monthly_cash_flow(transactions, date_range)
    if monthly.empty:
        st.info("Cash flow chart will appear after transactions are available for this period.")
        return

    ordered = monthly.sort_values("period_order")
    pivot = ordered.pivot(index="period_label", columns="flow", values="amount")
    st.bar_chart(pivot)


def render_category_breakdown(transactions: pd.DataFrame) -> None:
    if transactions is None or transactions.empty:
        st.info("No data available for selected filters.")
        return

    st.markdown("#### Category Pressure")
    breakdown = build_category_breakdown(transactions, top_n=6)
    if breakdown.empty:
        st.info("Categories unavailable; upload data to see top categories.")
        return
    st.bar_chart(breakdown.set_index("label")["amount"])


def _latest_delta(df: pd.DataFrame, column: str) -> tuple[Optional[float], Optional[float], Optional[int]]:
    ordered = df.sort_values("year")
    if ordered.empty or column not in ordered.columns:
        return None, None, None
    latest_row = ordered.iloc[-1]
    prior_row = ordered.iloc[-2] if len(ordered.index) > 1 else None
    latest_value = float(latest_row[column])
    if prior_row is None:
        return latest_value, None, None
    delta_value = latest_value - float(prior_row[column])
    return latest_value, delta_value, int(prior_row["year"])


def _render_yoy_metric_block(title: str, df: pd.DataFrame, column: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        if df.empty or column not in df.columns:
            st.info("Upload data to view year-over-year analytics.")
            return

        chart_data = df.set_index("year")[[column]]
        st.bar_chart(chart_data)

        latest_value, delta_value, prior_year = _latest_delta(df, column)
        delta_pct = None
        prior_value = None
        if prior_year is not None:
            prior_value = float(df.loc[df["year"] == prior_year, column].iloc[0])
            if prior_value != 0:
                delta_pct = (delta_value / prior_value) * 100 if delta_value is not None else None

        delta_display = "No prior year"
        if delta_value is not None and prior_year is not None:
            delta_display = f"{_format_currency(delta_value)} vs {prior_year}"
        st.metric(
            "Latest",
            _format_currency(latest_value or 0.0),
            delta=delta_display,
        )
        if delta_pct is not None and prior_year is not None:
            st.caption(f"Δ % vs {prior_year}: {delta_pct:.1f}%")
        else:
            st.caption("Δ % vs prior year: N/A")


def render_yoy_analytics(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    months_filter: set[int],
    selected_period: str,
) -> None:
    if transactions is None or transactions.empty:
        st.info("No data available for selected filters.")
        return

    st.markdown("#### Year-over-Year Analytics")

    preset = "full_year" if selected_period.upper() == ALL_YEARS_LABEL else selected_period.lower()
    balance_trends = build_yearly_balance_trends(accounts, preset=preset)
    flow_trends = build_yearly_income_expense(
        transactions,
        months=months_filter if selected_period.upper() in _QUARTER_MONTHS else None,
    )

    balance_cols = st.columns(3)
    for col, (title, field) in zip(
        balance_cols, [("Net Worth", "net_worth"), ("Assets", "assets"), ("Liabilities", "liabilities")]
    ):
        with col:
            _render_yoy_metric_block(title, balance_trends, field)

    flow_cols = st.columns(2)
    for col, (title, field) in zip(flow_cols, [("Income", "income"), ("Expenses", "expenses")]):
        with col:
            _render_yoy_metric_block(title, flow_trends, field)


def render_dashboard_tab(
    transactions_df: Optional[pd.DataFrame],
    accounts_df: Optional[pd.DataFrame],
    *,
    year_label: str,
    selected_period: str,
    date_range: Tuple[date, date],
    months_filter: set[int],
) -> None:
    """Render the dashboard tab without triggering ingestion or layout resets."""
    transactions = _coerce_dataframe(transactions_df)
    accounts = _coerce_dataframe(accounts_df)

    _render_header(year_label, selected_period, date_range)
    if transactions.empty and accounts.empty:
        st.info("Upload transactions and accounts CSVs to enable full dashboard features.")
        return

    render_key_metrics(transactions)
    render_monthly_cash_flow(transactions, date_range)
    render_category_breakdown(transactions)

    if year_label == ALL_YEARS_LABEL:
        render_yoy_analytics(
            transactions,
            accounts,
            months_filter,
            selected_period,
        )
