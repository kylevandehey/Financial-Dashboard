# src/transactions/page.py

import streamlit as st
import pandas as pd

from src.dashboard.sections.charts import render_charts
from src.dashboard.date_controls import render_date_controls


def render_transactions_page(transactions: pd.DataFrame) -> None:
    st.markdown("# Transactions")
    st.markdown("## Explore, filter, and analyze your data")

    if transactions is None or transactions.empty:
        st.info("No transactions available. Upload Monarch CSV exports to begin.")
        return

    # -------------------------------------------------
    # Date Controls (shared contract)
    # -------------------------------------------------
    filtered_tx, start_date, end_date, selected_label = render_date_controls(
        transactions
    )

    if filtered_tx is None or filtered_tx.empty:
        st.info("No transactions in selected date range.")
        return

    st.divider()

    # -------------------------------------------------
    # Charts + Controls (NOW OWNED BY TRANSACTIONS)
    # -------------------------------------------------
    render_charts(filtered_tx=filtered_tx)
