# src/dashboard/sections/snapshot.py

import streamlit as st
import pandas as pd

from src.cash_flow import compute_cash_flow
from src.formatting import format_currency


def render_snapshot_section(transactions: pd.DataFrame) -> None:
    """
    High-level financial snapshot.
    Respects the active date range (transactions already filtered upstream).
    """

    if transactions.empty:
        st.info("No transactions available for this date range.")
        return

    result = compute_cash_flow(transactions)

    st.markdown("## Snapshot")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            label="Income",
            value=format_currency(result.income),
        )

    with c2:
        st.metric(
            label="Expenses",
            value=format_currency(result.net_expenses),
        )

    with c3:
        st.metric(
            label="Net Cash Flow",
            value=format_currency(result.net_cash),
        )
