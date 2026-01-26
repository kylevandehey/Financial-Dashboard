# src/dashboard/sections/snapshot.py

import streamlit as st


def render_snapshot(cash_flow) -> None:
    """
    High-level snapshot block.
    Detailed metrics live elsewhere.
    """
    if cash_flow is None:
        return

    st.markdown("## Snapshot")
    st.caption("High-level summary for the selected date range.")
