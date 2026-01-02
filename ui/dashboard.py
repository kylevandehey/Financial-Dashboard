"""Streamlit dashboard tab with defensive rendering."""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL


def _coerce_dataframe(data: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Return a copy of the incoming data or an empty frame."""
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def _infer_date_range(transactions: pd.DataFrame) -> tuple[date, date]:
    """Infer the available date range, falling back to today when missing."""
    today = date.today()
    if transactions.empty or "date" not in transactions.columns:
        return today, today

    dates = pd.to_datetime(transactions["date"], errors="coerce").dropna()
    if dates.empty:
        return today, today

    return dates.min().date(), dates.max().date()


def _filter_by_year(df: pd.DataFrame, year_label: Optional[str]) -> pd.DataFrame:
    """Filter transactions by the selected year label."""
    if df.empty or year_label in (None, ALL_YEARS_LABEL):
        return df

    if "year" not in df.columns:
        return df

    try:
        year_int = int(year_label)
    except (TypeError, ValueError):
        return df

    return df.loc[df["year"] == year_int].copy()


def _format_currency(value: float) -> str:
    """Format currency using accounting style for negatives."""
    amount = float(value or 0)
    formatted = f"${abs(amount):,.2f}"
    return f"({formatted})" if amount < 0 else formatted


def _render_header(year_label: str) -> None:
    """Render the dashboard heading and scope context."""
    st.markdown("### Dashboard Overview")
    st.caption(
        "Baseline dashboard view with defensive rendering to keep the app online while sections return incrementally."
    )
    if year_label:
        st.caption(f"Scope: {year_label}")


def _render_global_controls(transactions: pd.DataFrame, year_label: str) -> None:
    """Render date and scope controls with safe defaults."""
    start_date, end_date = _infer_date_range(transactions)
    st.markdown("#### Global Controls")

    with st.container(border=True):
        col1, col2, col3 = st.columns([1.2, 1.2, 1.6])

        with col1:
            st.write("Date Range")
            st.date_input(
                "Start / End",
                (start_date, end_date),
                key=f"dashboard_date_{year_label or 'all'}",
            )

        with col2:
            st.write("Preset")
            st.selectbox(
                "Presets",
                ["YTD", "MTD", "Q1", "Q2", "Q3", "Q4", "All"],
                index=0,
                key=f"dashboard_preset_{year_label or 'all'}",
            )

        with col3:
            st.write("Status")
            if transactions.empty:
                st.info("No transactions detected. Upload CSVs to unlock charts.")
            else:
                st.success("Transactions loaded")
            st.caption("Scope respects the selected year tab.")


def _render_configuration(transactions: pd.DataFrame) -> None:
    """Show transaction configuration placeholders."""
    st.markdown("#### Configure Transactions")
    with st.container(border=True):
        st.write("Configure how transactions feed the dashboard.")
        st.checkbox("Include transfers", value=True, key="dashboard_include_transfers")
        st.checkbox("Include refunds", value=True, key="dashboard_include_refunds")
        st.caption("These toggles are placeholders to keep the configuration section visible during recovery.")


def _render_key_metrics(transactions: pd.DataFrame) -> None:
    """Render headline metrics with accounting-style formatting."""
    st.markdown("#### Key Metrics")
    with st.container(border=True):
        amount_series = pd.to_numeric(
            transactions.get("amount", pd.Series(dtype=float, index=transactions.index)),
            errors="coerce",
        )
        total_count = len(transactions.index)
        total_income = amount_series[amount_series > 0].sum() if not amount_series.empty else 0.0
        total_expense = amount_series[amount_series < 0].sum() if not amount_series.empty else 0.0
        net = amount_series.sum() if not amount_series.empty else 0.0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Transactions", f"{total_count:,}")
        col2.metric("Income", _format_currency(total_income))
        col3.metric("Expenses", _format_currency(total_expense))
        col4.metric("Net Cash Flow", _format_currency(net))


def _render_charts(transactions: pd.DataFrame) -> None:
    """Render charts safely, skipping sections that cannot run."""
    st.markdown("#### Charts (Recovery Mode)")
    if transactions.empty:
        st.info("Charts will appear after CSV upload. No data available yet.")
        return

    with st.container(border=True):
        try:
            if "date" in transactions.columns:
                cash_flow = transactions.copy()
                cash_flow["date"] = pd.to_datetime(cash_flow["date"], errors="coerce")
                cash_flow = cash_flow.dropna(subset=["date"])
                if cash_flow.empty:
                    st.info("Not enough date data for cash flow chart.")
                else:
                    monthly = (
                        cash_flow.groupby(cash_flow["date"].dt.to_period("M"))
                        .agg(total_amount=("amount", "sum"))
                        .reset_index()
                    )
                    monthly["month"] = monthly["date"].dt.to_timestamp()
                    monthly.set_index("month", inplace=True)
                    st.bar_chart(monthly["total_amount"])
            else:
                st.info("No date column found; skipping cash flow chart.")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Cash flow chart skipped: {exc}")

        try:
            if "category" in transactions.columns and not transactions["category"].dropna().empty:
                category_summary = (
                    transactions.groupby("category")
                    .agg(total_amount=("amount", "sum"))
                    .sort_values("total_amount", ascending=False)
                    .head(5)
                )
                st.area_chart(category_summary)
            else:
                st.info("Categories unavailable; skipping category trend chart.")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Category chart skipped: {exc}")


def render_dashboard_tab(transactions_df: Optional[pd.DataFrame], accounts_df: Optional[pd.DataFrame], year_label: Optional[str] = None) -> None:
    """Safely render the dashboard tab without crashing during import or initial load."""
    transactions = _coerce_dataframe(transactions_df)
    accounts = _coerce_dataframe(accounts_df)

    year_context = year_label or ALL_YEARS_LABEL
    scoped_transactions = _filter_by_year(transactions, year_context)

    _render_header(year_context)
    _render_global_controls(scoped_transactions, year_context)
    _render_configuration(scoped_transactions)
    _render_key_metrics(scoped_transactions)
    _render_charts(scoped_transactions)

    if scoped_transactions.empty and transactions.empty and accounts.empty:
        st.info("Upload transactions and accounts CSVs to enable full dashboard features.")


if __name__ == "__main__":
    print("dashboard.py imports successfully")
