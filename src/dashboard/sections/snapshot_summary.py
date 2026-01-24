import streamlit as st
from src.cash_flow import compute_cash_flow
from src.formatting import format_currency


def render_snapshot_summary(transactions):
    if transactions.empty:
        return

    result = compute_cash_flow(transactions)

    st.markdown("## Snapshot")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Income", format_currency(result.income))

    with c2:
        st.metric("Expenses", format_currency(result.net_expenses))

    with c3:
        st.metric("Net Cash Flow", format_currency(result.net_cash))
