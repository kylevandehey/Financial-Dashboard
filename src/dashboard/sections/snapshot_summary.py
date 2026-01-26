# src/dashboard/sections/snapshot_summary.py

import streamlit as st
import pandas as pd


def render_snapshot_summary(filtered_tx: pd.DataFrame) -> None:
    """
    Snapshot details section.
    """
    if filtered_tx is None or filtered_tx.empty:
        st.info("No transactions in selected date range.")
        return

    st.markdown("## Snapshot Details")
    st.caption("Additional breakdowns will live here.")
