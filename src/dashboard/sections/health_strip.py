# src/dashboard/sections/health_strip.py

import streamlit as st
import pandas as pd

from src.cash_flow import compute_cash_flow
from src.formatting import format_currency


def _safe_pct(numer: float, denom: float) -> float:
    if denom == 0:
        return 0.0
    return (numer / denom) * 100.0


def render_health_strip(transactions: pd.DataFrame) -> None:
    """
    Financial Health strip must match Snapshot calculations exactly.
    Therefore, it uses compute_cash_flow() (canonical rules) rather than
    naive amount sign logic.
    """
    if transactions is None or transactions.empty or "amount" not in transactions.columns:
        return

    r = compute_cash_flow(transactions)

    income = float(r.income)
    expenses = float(r.net_expenses)  # canonical "net expenses" value
    net = float(r.net_cash)

    # Savings rate = Net / Income (common convention); negative if net < 0
    savings_rate = _safe_pct(net, income)

    st.markdown("### 🩺 Financial Health")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Income", format_currency(income))
    with c2:
        st.metric("Expenses", format_currency(expenses))
    with c3:
        st.metric("Net Cash Flow", format_currency(net))
    with c4:
        st.metric("Savings Rate", f"{savings_rate:.1f}%")
