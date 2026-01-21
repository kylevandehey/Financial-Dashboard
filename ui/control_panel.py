"""
UI Control Panel (Sidebar)

Purpose
- Handle CSV uploads (Transactions + Balances)
- Normalize to canonical DataFrames via src.ingest
- Persist canonical data in session state for all tabs

Important
- This module should NOT implement cash flow logic.
- This module should NOT implement dashboard date presets.
  (Date preset bar lives in ui/dashboard.py.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import date as date_cls

import streamlit as st
import pandas as pd

from src.ingest import (
    identify_csv_roles,
    normalize_transactions,
    normalize_accounts,
)


@dataclass(frozen=True)
class ControlState:
    transactions: pd.DataFrame
    accounts: pd.DataFrame


def _init_state() -> None:
    if "canonical_transactions" not in st.session_state:
        st.session_state["canonical_transactions"] = pd.DataFrame()
    if "canonical_accounts" not in st.session_state:
        st.session_state["canonical_accounts"] = pd.DataFrame()
    if "upload_diagnostics" not in st.session_state:
        st.session_state["upload_diagnostics"] = []
    if "upload_error" not in st.session_state:
        st.session_state["upload_error"] = None


def render_control_panel() -> ControlState:
    """
    Sidebar: upload + ingestion only.

    Returns
    -------
    ControlState
        Canonical transactions + accounts DataFrames from session state.
    """
    _init_state()

    with st.sidebar:
        st.markdown("## Upload Monarch CSVs")
        st.caption("Upload both **Transactions** and **Balances/Accounts** CSV exports.")

        uploaded_files = st.file_uploader(
            "Upload Transactions + Balances CSVs",
            type=["csv"],
            accept_multiple_files=True,
            help="Upload both Monarch Money Transactions and Balances/Accounts CSV exports.",
            key="cp_file_uploader",
        )

        if uploaded_files:
            tx_buf, bal_buf, diagnostics, error_message = identify_csv_roles(uploaded_files)

            st.session_state["upload_diagnostics"] = diagnostics
            st.session_state["upload_error"] = error_message

            if error_message:
                st.error(error_message)
            else:
                try:
                    tx_df = normalize_transactions(tx_buf)
                    bal_df = normalize_accounts(bal_buf)
                except Exception as exc:
                    st.session_state["upload_error"] = str(exc)
                    st.error(f"Upload processing failed: {exc}")
                else:
                    st.session_state["canonical_transactions"] = tx_df
                    st.session_state["canonical_accounts"] = bal_df
                    st.success("CSV upload processed. Dashboard refreshed.")

        # Optional: diagnostics expander (helpful during rebuild)
        with st.expander("Upload diagnostics", expanded=False):
            if st.session_state.get("upload_error"):
                st.warning("Upload error detected (see above).")
            diags = st.session_state.get("upload_diagnostics", [])
            if not diags:
                st.caption("No diagnostics yet.")
            else:
                rows = []
                for d in diags:
                    rows.append(
                        {
                            "File": d.name,
                            "Transactions Match": d.transactions_match,
                            "Balances Match": d.balances_match,
                            "Tx Missing": ", ".join(d.transactions_missing or []),
                            "Bal Missing": ", ".join(d.balances_missing or []),
                        }
                    )
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

    return ControlState(
        transactions=st.session_state["canonical_transactions"],
        accounts=st.session_state["canonical_accounts"],
    )
