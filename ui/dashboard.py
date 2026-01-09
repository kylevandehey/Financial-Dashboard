import streamlit as st
import pandas as pd
from datetime import date
from typing import Optional

from src.formatting import format_currency, format_date_range


def _coerce_dataframe(data: Optional[pd.DataFrame]) -> pd.DataFrame:
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def render_dashboard_tab(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame | None,
    date_range: tuple[date, date] | None,
    *,
    year_label: str,
    selected_period: str,
    **_ignored: object,
) -> None:
    st.markdown("### Dashboard Overview")
    st.caption(f"Scope: {year_label} · Period: {selected_period}")

    if date_range:
        st.caption("Date Range")
        st.caption(format_date_range(date_range))

    df = _coerce_dataframe(transactions)

    if df.empty or "amount" not in df.columns:
        st.info("Upload a Transactions CSV with an Amount column to begin.")
        return

    # Baseline truth metrics (NO filters, NO categories, NO charts)
    income = float(df.loc[df["amount"] > 0, "amount"].sum())
    expenses = float(df.loc[df["amount"] < 0, "amount"].sum())
    expenses_abs = abs(expenses)
    net = income - expenses_abs

    st.markdown("#### Key Metrics (Baseline)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Income", format_currency(income))
    c2.metric("Expenses", format_currency(expenses_abs))
    c3.metric("Net", format_currency(net))

    st.caption("Baseline mode: this ignores all transaction-type logic (transfers/CC payments/refunds). That will be reintroduced after baseline is correct.")

