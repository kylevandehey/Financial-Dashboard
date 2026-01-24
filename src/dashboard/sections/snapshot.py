# src/dashboard/sections/snapshot_summary.py

import streamlit as st
import pandas as pd


def render_snapshot_summary(transactions: pd.DataFrame) -> None:
    """
    Snapshot section wrapper.

    We intentionally do NOT show Income/Expenses/Net metrics here anymore,
    because those are now owned by the Financial Health strip to avoid
    duplicate/conflicting summaries.
    """
    st.markdown("## Snapshot")

    if transactions is None or transactions.empty:
        st.info("No transactions in selected date range.")
        return

    # Placeholder area (optional): you can add small narrative/notes later
    st.caption("Overview for the currently selected date range.")
