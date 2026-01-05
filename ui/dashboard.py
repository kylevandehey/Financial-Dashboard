import streamlit as st
import pandas as pd
import altair as alt

from datetime import date
from typing import Optional

from src.config import ALL_YEARS_LABEL
from src.formatting import format_currency, format_date_range
from src.metrics import (
    build_category_breakdown,
    build_monthly_cash_flow,
    build_yearly_balance_trends,
    build_yearly_income_expense,
    get_balances_snapshot,
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
    """
    Generate a deterministic, collision-safe Streamlit widget key.
    """
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


def _render_header(
    year_label: str,
    selected_period: str,
    date_range: tuple[date, date],
) -> None:
    st.markdown("### Dashboard Overview")
    st.caption(f"Scope: {year_label} · Period: {selected_period}")
    st.caption("Date Range")
    st.caption(format_date_range(date_range))


def _render_data_grid(
    df: pd.DataFrame,
    *,
    title: str,
    section_id: str | None,
    height: int | None = None,
) -> None:
    """Reusable, stateful collapsible data grid for tables under charts."""
    row_count = len(df.index) if df is not None else 0
    header = f"{title} ({row_count} rows)"

    # Non-collapsible fallback
    if section_id is None:
        st.markdown(f"**{header}**")
        st.dataframe(df, use_container_width=True, height=height)
        return

    expander_key = _safe_key("grid", section_id)
    expanded_default = st.session_state.get(expander_key, False)

    with st.expander(header, expanded=expanded_default, key=expander_key):
        st.dataframe(df, use_container_width=True, height=height)
def render_dashboard_tab(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    date_range: tuple[date, date],
    *,
    year_label: str,
    selected_period: str,
) -> None:
    """
    Entry-point renderer for the Dashboard tab.

    This function is intentionally thin and delegates rendering
    to internal helpers to preserve layout consistency.
    """

    # Header
    _render_header(
        year_label=year_label,
        selected_period=selected_period,
        date_range=date_range,
    )

    # Key metrics
    render_key_metrics(
        transactions=transactions,
        accounts=accounts,
        date_range=date_range,
    )

    st.divider()

    # Category breakdown
    category_df = build_category_breakdown(transactions, date_range)
    _render_data_grid(
        category_df,
        title="Category Breakdown",
        section_id=_make_section_id("categories", year_label, selected_period),
        height=420,
    )

    st.divider()

    # Monthly cash flow
    monthly_cf = build_monthly_cash_flow(transactions, date_range)
    _render_data_grid(
        monthly_cf,
        title="Monthly Cash Flow",
        section_id=_make_section_id("monthly_cash_flow", year_label, selected_period),
        height=420,
    )

    st.divider()

    # Yearly trends
    yearly_trends = build_yearly_balance_trends(accounts, date_range)
    _render_data_grid(
        yearly_trends,
        title="Yearly Balance Trends",
        section_id=_make_section_id("yearly_trends", year_label, selected_period),
        height=420,
    )
