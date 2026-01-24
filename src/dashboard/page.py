# src/dashboard/page.py

import streamlit as st
import pandas as pd

def render_dashboard_page(transactions: pd.DataFrame) -> None:
    """
    Entry point for the Dashboard tab.
    This file intentionally contains NO business logic.
    It only orchestrates dashboard sections.
    """

    st.title("Dashboard (Core Rebuild)")
    st.subheader("Dashboard Overview")

    if transactions is None or transactions.empty:
        st.info("No transactions available for dashboard.")
        return

    # Temporary placeholder content
    st.markdown("✅ Dashboard page loaded successfully.")
    st.markdown("Next step: extract Snapshot section into dashboard/sections/")

