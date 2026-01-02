"""Persistent control panel and ingestion pipeline shared across all tabs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL
from src.filters import compute_scope_date_range, period_options_for_scope, reset_transaction_filter_config
from src.ingest import identify_csv_roles, normalize_accounts, normalize_transactions
from ui.transaction_filters import render_transaction_filters


_QUARTER_MONTHS: dict[str, set[int]] = {
    "Q1": {1, 2, 3},
    "Q2": {4, 5, 6},
    "Q3": {7, 8, 9},
    "Q4": {10, 11, 12},
}


_SESSION_KEYS_TO_CLEAR: Sequence[str] = (
    "transactions_df",
    "accounts_df",
    "filtered_transactions",
    "filtered_accounts",
    "period_selection",
    "monarch_csvs",
    "upload_signature",
    "ingestion_status",
    "ingestion_error",
    "tx_filters",
    "transactions_search_term",
    "transactions_categories",
    "transactions_accounts",
    "dashboard_configure_excluded_types",
    "dashboard_configure_include_keywords",
    "dashboard_configure_exclude_keywords",
    "dashboard_configure_include_transfers",
    "dashboard_configure_include_refunds",
)


@dataclass
class ControlPanelState:
    transactions: pd.DataFrame
    accounts: pd.DataFrame
    selected_period: str
    date_range: tuple[date, date]
    months_filter: set[int]
    status: str | None = None
    error: str | None = None


def _coerce_dataframe(data: pd.DataFrame | None) -> pd.DataFrame:
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def _upload_signature(files: Iterable) -> tuple[str, ...] | None:
    materialized = list(files or [])
    if not materialized:
        return None
    signatures = []
    for upload in materialized:
        name = getattr(upload, "name", "uploaded.csv")
        payload = upload.getvalue() if hasattr(upload, "getvalue") else b""
        signatures.append(f"{name}:{len(payload)}")
    return tuple(sorted(signatures))


def _ingest_csv_uploads(uploaded_files: Iterable) -> tuple[pd.DataFrame, pd.DataFrame, str | None, str | None]:
    """Ingest uploaded CSVs once per change and persist them to session state."""
    existing_transactions = _coerce_dataframe(st.session_state.get("transactions_df"))
    existing_accounts = _coerce_dataframe(st.session_state.get("accounts_df"))

    signature = _upload_signature(uploaded_files)
    last_signature = st.session_state.get("upload_signature")
    if signature is None:
        return existing_transactions, existing_accounts, st.session_state.get("ingestion_status"), st.session_state.get("ingestion_error")

    if signature == last_signature:
        return existing_transactions, existing_accounts, st.session_state.get("ingestion_status"), st.session_state.get("ingestion_error")

    transactions_file, accounts_file, _diagnostics, identification_error = identify_csv_roles(uploaded_files)
    if transactions_file is None:
        readable_error = identification_error or "Upload a Transactions CSV with Date and Amount columns to continue."
        st.session_state["ingestion_error"] = readable_error
        st.session_state["ingestion_status"] = None
        return existing_transactions, existing_accounts, None, readable_error

    transactions_df = existing_transactions
    accounts_df = pd.DataFrame()
    error_message = None
    status_message = None

    try:
        transactions_df = normalize_transactions(transactions_file)
    except ValueError as exc:
        error_message = f"Transactions CSV error: {exc}"

    if accounts_file is not None:
        try:
            accounts_df = normalize_accounts(accounts_file)
        except ValueError as exc:
            error_message = f"Accounts CSV error: {exc}"
    else:
        status_message = identification_error or "Transactions loaded. Upload balances CSV to unlock assets and liabilities."

    if error_message:
        st.session_state["ingestion_error"] = error_message
        st.session_state["ingestion_status"] = None
        return existing_transactions, existing_accounts, None, error_message

    st.session_state["accounts_df"] = accounts_df
    st.session_state["transactions_df"] = transactions_df
    st.session_state["upload_signature"] = signature
    st.session_state["ingestion_error"] = None
    st.session_state["ingestion_status"] = status_message or "CSV upload processed. Dashboard refreshed."
    return transactions_df, accounts_df, st.session_state["ingestion_status"], None


def reset_dashboard_state() -> None:
    """Clear CSV-derived session state without forcing a reload loop."""
    for key in _SESSION_KEYS_TO_CLEAR:
        if key in st.session_state:
            st.session_state.pop(key, None)
    # Clear cached transaction filters and uploader buffers explicitly
    st.session_state["monarch_csvs"] = None
    reset_transaction_filter_config()


def _months_for_period(period_label: str) -> set[int]:
    normalized = str(period_label or "").upper()
    return _QUARTER_MONTHS.get(normalized, set())


def render_control_panel() -> ControlPanelState:
    """Render a persistent sidebar panel that handles ingestion and selections."""
    st.sidebar.markdown("### Control Panel")

    reset_clicked = st.sidebar.button("Reset Dashboard", use_container_width=True)
    if reset_clicked:
        reset_dashboard_state()
        st.sidebar.success("Dashboard reset. Upload CSVs to begin.")

    uploaded_files = st.sidebar.file_uploader(
        "Upload Monarch CSVs (Transactions + Balances)",
        accept_multiple_files=True,
        type=["csv"],
        key="monarch_csvs",
    )

    transactions_df, accounts_df, status_message, error_message = _ingest_csv_uploads(uploaded_files)

    period_options = period_options_for_scope(ALL_YEARS_LABEL)
    default_period = st.session_state.get("period_selection") or period_options[0]
    if default_period not in period_options:
        default_period = period_options[0]
    period_container = st.sidebar.container()
    period_container.markdown("#### Period Selection")
    selected_period = period_container.radio(
        "Period Selection",
        period_options,
        index=period_options.index(default_period),
        key="period_selection",
        horizontal=True,
        label_visibility="collapsed",
    )

    date_bounds = compute_scope_date_range(
        transactions_df,
        year_label=ALL_YEARS_LABEL,
        period_label=selected_period,
        fallback_df=accounts_df,
    )
    months_filter = _months_for_period(selected_period)

    st.sidebar.write("Date Range")
    st.sidebar.caption(f"{date_bounds[0].strftime('%b %d, %Y')} → {date_bounds[1].strftime('%b %d, %Y')}")

    st.sidebar.write("Status")
    if error_message:
        st.sidebar.error(error_message)
    elif status_message:
        if "Upload balances" in status_message or "Could not identify both required CSVs" in status_message:
            st.sidebar.warning(status_message)
        else:
            st.sidebar.success(status_message)
    elif transactions_df.empty and accounts_df.empty:
        st.sidebar.warning("Upload Transactions and Balances CSVs to unlock analytics.")
    else:
        st.sidebar.info("Data ready.")

    st.sidebar.markdown("---")
    render_transaction_filters(target=st.sidebar)
    st.sidebar.markdown("---")
    st.sidebar.caption("Controls stay pinned for all tabs.")

    return ControlPanelState(
        transactions=_coerce_dataframe(transactions_df),
        accounts=_coerce_dataframe(accounts_df),
        selected_period=selected_period,
        date_range=date_bounds,
        months_filter=months_filter,
        status=status_message,
        error=error_message,
    )
