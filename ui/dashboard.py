import streamlit as st
import pandas as pd
import altair as alt

from datetime import date
from typing import Optional

from src.formatting import format_currency, format_date_range
from src.metrics import (
    build_category_breakdown,
    build_monthly_cash_flow,
    build_yearly_balance_trends,
    summarize_cash_flow,
    summarize_accounts,
)

# -----------------------------
# Constants
# -----------------------------

_QUARTER_MONTHS: dict[str, set[int]] = {
    "Q1": {1, 2, 3},
    "Q2": {4, 5, 6},
    "Q3": {7, 8, 9},
    "Q4": {10, 11, 12},
}

# -----------------------------
# Helpers
# -----------------------------


def _make_section_id(section: str, year_label: str, selected_period: str) -> str:
    normalized = f"{section}_{year_label}_{selected_period}".lower().replace(" ", "_")
    return f"dashboard_{normalized}"


def _safe_key(prefix: str, section_id: str | None) -> str:
    """Generate a deterministic, collision-safe Streamlit widget key."""
    sid = (section_id or "default").strip().lower().replace(" ", "_")
    return f"{prefix}__{sid}"


def _coerce_dataframe(data: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Return a copy of the incoming data or an empty frame."""
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def _currency_axis(title: str | None = None) -> alt.Axis:
    """Altair axis with accounting-style label formatting."""
    return alt.Axis(
        title=title,
        labelExpr=(
            "datum.value < 0 "
            "? '($' + format(-datum.value, ',.2f') + ')' "
            ": '$' + format(datum.value, ',.2f')"
        ),
    )

# -----------------------------
# UI Sections
# -----------------------------


def _render_header(
    year_label: str,
    selected_period: str,
    date_range: tuple[date, date],
) -> None:
    st.markdown("### Dashboard Overview")
    st.caption(f"Scope: {year_label} · Period: {selected_period}")
    st.caption("Date Range")
    st.caption(format_date_range(date_range))


def render_key_metrics(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    date_range: tuple[date, date],
    **_ignored: object,
) -> None:
    """Render headline metrics with consistent grouping and accounting formatting."""

    if (transactions is None or transactions.empty) and (accounts is None or accounts.empty):
        st.info(
            "No data available for selected filters. "
            "Metrics shown below use zero values until data is uploaded."
        )

    st.markdown("#### Key Metrics")

    totals = summarize_cash_flow(transactions, date_range)

    account_summary = summarize_accounts(
        accounts,
        end_date=date_range[1] if accounts is not None else None,
    )

    assets = float(account_summary.get("total_assets", 0.0))
    liabilities = float(account_summary.get("total_liabilities", 0.0))
    equity = float(account_summary.get("net_worth", assets + liabilities))

    start_date, end_date = date_range
    start_label = start_date.strftime("%b %d, %Y")
    end_label = end_date.strftime("%b %d, %Y")

    transaction_count = len(transactions.index) if transactions is not None else 0
    st.caption(f"{transaction_count:,} transactions in scope · {start_label} → {end_label}")

    cash_flow_group, balance_sheet_group = st.columns(2)

    with cash_flow_group:
        st.markdown("**Cash Flow**")
        income_col, expense_col, net_col = st.columns(3)
        with income_col:
            st.metric("Income", format_currency(totals.income))
        with expense_col:
            st.metric("Expenses", format_currency(totals.expenses))
        with net_col:
            st.metric("Net", format_currency(totals.net))

    with balance_sheet_group:
        st.markdown("**Balances**")
        asset_col, liability_col, equity_col = st.columns(3)
        with asset_col:
            st.metric("Assets", format_currency(assets))
        with liability_col:
            st.metric("Liabilities", format_currency(liabilities))
        with equity_col:
            st.metric("Equity", format_currency(equity))


def _render_data_grid(
    df: pd.DataFrame,
    *,
    title: str,
    section_id: str | None,
    height: int | None = None,
) -> None:
    """Reusable, stateful collapsible data grid for tables under charts."""
    df = _coerce_dataframe(df)
    row_count = len(df.index)
    header = f"{title} ({row_count} rows)"

    if section_id is None:
        st.markdown(f"**{header}**")
        st.dataframe(df, use_container_width=True, height=height)
        return

    expander_key = _safe_key("grid", section_id)
    expanded_default = bool(st.session_state.get(expander_key, False))

    with st.expander(header, expanded=expanded_default, key=expander_key):
        st.dataframe(df, use_container_width=True, height=height)

# -----------------------------
# Entry Point
# -----------------------------


def render_dashboard_tab(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    date_range: tuple[date, date],
    *,
    year_label: str,
    selected_period: str,
    **_ignored: object,
) -> None:
    """
    Entry-point renderer for the Dashboard tab.
    """

    _render_header(
        year_label=year_label,
        selected_period=selected_period,
        date_range=date_range,
    )

    render_key_metrics(
        transactions=transactions,
        accounts=accounts,
        date_range=date_range,
    )

    st.divider()

    category_df = build_category_breakdown(transactions, date_range)
    _render_data_grid(
        category_df,
        title="Category Breakdown",
        section_id=_make_section_id("categories", year_label, selected_period),
        height=420,
    )

    st.divider()

    monthly_cf = build_monthly_cash_flow(transactions, date_range)
    _render_data_grid(
        monthly_cf,
        title="Monthly Cash Flow",
        section_id=_make_section_id("monthly_cash_flow", year_label, selected_period),
        height=420,
    )

    st.divider()

    yearly_trends = build_yearly_balance_trends(accounts, date_range)
    _render_data_grid(
        yearly_trends,
        title="Yearly Balance Trends",
        section_id=_make_section_id("yearly_trends", year_label, selected_period),
        height=420,
    )
