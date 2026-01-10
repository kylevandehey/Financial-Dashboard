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


# -----------------------------
# UI
# -----------------------------

def render_dashboard_tab(
    transactions: pd.DataFrame,
    *,
    available_years: list[str],
    date_range: tuple[date, date] | None = None,  # ignored intentionally
) -> None:
    """
    Core rebuild dashboard (TRUE baseline).

    Rules:
    - Income = sum(amount > 0)
    - Expenses = sum(abs(amount < 0))
    - Net = Income - Expenses
    - NO transaction-type logic
    - NO category logic
    - NO external date filtering
    - Year tabs are the ONLY filter
    """

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

            # -----------------------------
            # TRUE Baseline Metrics
            # -----------------------------

            amounts = pd.to_numeric(
                scoped_tx["amount"],
                errors="coerce"
            ).fillna(0.0)

            positive = amounts[amounts > 0]
            negative = amounts[amounts < 0]

            income = float(positive.sum())
            expenses = float((-negative).sum())
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
                f"Audit → Positive rows: {len(positive)} | "
                f"Negative rows: {len(negative)}"
            )


