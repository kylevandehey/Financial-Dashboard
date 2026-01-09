import streamlit as st
import pandas as pd
from datetime import date

from src.formatting import format_currency, format_date_range


# -----------------------------
# Helpers
# -----------------------------

def _coerce_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    return pd.DataFrame(df).copy()


def _filter_by_year(df: pd.DataFrame, year_label: str) -> pd.DataFrame:
    if df.empty:
        return df
    if year_label == "ALL YEARS":
        return df
    if "year" not in df.columns:
        return df
    try:
        year = int(year_label)
    except ValueError:
        return df
    return df[df["year"] == year]


# -----------------------------
# UI
# -----------------------------

def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
    date_range: tuple[date, date],
) -> None:
    """
    Core rebuild dashboard (TRUE baseline).

    Rules:
    - Income = sum(amount > 0)
    - Expenses = sum(abs(amount < 0))
    - Net = Income - Expenses
    - NO transaction-type logic
    - NO category logic
    - Year tabs are the ONLY filter
    """

    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    # -----------------------------
    # Year Tabs (AUDIT CONTROL)
    # -----------------------------

    year_tabs = st.tabs(available_years)

    for tab, year_label in zip(year_tabs, available_years):
        with tab:
            scoped_tx = _filter_by_year(_coerce_df(transactions), year_label)

            st.caption(f"Scope: {year_label}")
            st.caption("Date Range")
            st.caption(format_date_range(date_range))

            if scoped_tx.empty or "amount" not in scoped_tx.columns:
                st.info("No transactions in scope.")
                continue

            # -----------------------------
            # TRUE Baseline Metrics
            # -----------------------------

            amounts = pd.to_numeric(
                scoped_tx["amount"],
                errors="coerce"
            ).fillna(0.0)

            income = float(amounts[amounts > 0].sum())
            expenses = float((-amounts[amounts < 0]).sum())
            net = float(income - expenses)

            st.markdown("### Key Metrics (Baseline)")

            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric("Income", format_currency(income))

            with c2:
                st.metric("Expenses", format_currency(expenses))

            with c3:
                st.metric("Net", format_currency(net))

            # -----------------------------
            # Audit helpers (TEMPORARY)
            # -----------------------------

            st.caption(
                "Baseline mode: "
                "Income = sum(amount > 0), "
                "Expenses = sum(abs(amount < 0)). "
                "No transfer / CC / refund logic."
            )

            st.caption(
                f"Audit → Positive rows: {(amounts > 0).sum()} | "
                f"Negative rows: {(amounts < 0).sum()}"
            )

