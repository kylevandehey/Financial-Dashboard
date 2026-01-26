# src/dashboard/sections/health_strip.py

import streamlit as st
from src.formatting import format_currency


def _safe_pct(numer: float, denom: float) -> float:
    if denom == 0:
        return 0.0
    return (numer / denom) * 100.0


def render_health_strip(
    cash_flow,
    start_date=None,
    end_date=None,
    selected_label=None,
) -> None:
    """
    Financial Health strip.
    Expects canonical cash_flow object (already computed upstream).
    """
    if cash_flow is None:
        return

    income = float(cash_flow.income)
    expenses = float(cash_flow.net_expenses)
    net = float(cash_flow.net_cash)

    savings_rate = _safe_pct(net, income)

    st.markdown("### Financial Health")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Income", format_currency(income))
    with c2:
        st.metric("Expenses", format_currency(expenses))
    with c3:
        st.metric("Net Cash Flow", format_currency(net))
    with c4:
        st.metric("Savings Rate", f"{savings_rate:.1f}%")
