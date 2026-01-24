# src/dashboard/sections/health_strip.py

import streamlit as st
import pandas as pd
from src.formatting import format_currency


def render_health_strip(transactions: pd.DataFrame):
    """
    High-level financial health indicators.
    Designed to be lightweight and non-breaking.
    """

    if transactions.empty:
        st.info("No data available for health metrics.")
        return

    income = transactions.loc[transactions["amount"] > 0, "amount"].sum()
    expenses = transactions.loc[transactions["amount"] < 0, "amount"].sum() * -1
    net = income - expenses

    savings_rate = (net / income) if income else 0.0

    st.markdown("### 🩺 Financial Health")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Income", format_currency(income))

    with c2:
        st.metric("Expenses", format_currency(expenses))

    with c3:
        st.metric("Net Cash Flow", format_currency(net))

    with c4:
        st.metric("Savings Rate", f"{savings_rate:.1%}")
