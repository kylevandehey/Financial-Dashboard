"""Benchmarking tab for comparing Control Tower investments vs S&P 500."""

from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import ALL_YEARS_LABEL
from src.date_filters import compute_date_range, filter_dataframe_by_date


def _mock_sp500_series(dates: Iterable[pd.Timestamp]) -> pd.Series:
    base = 1000
    return pd.Series([base + idx * 5 for idx, _ in enumerate(dates)], index=dates)


def _prepare_investment_balances(accounts: pd.DataFrame) -> pd.DataFrame:
    if accounts is None or accounts.empty:
        return pd.DataFrame(columns=["date", "balance"])

    if "type" not in accounts.columns or "balance" not in accounts.columns:
        return pd.DataFrame(columns=["date", "balance"])

    investment_accounts = accounts.loc[accounts["type"].str.contains("invest", case=False, na=False)]
    if investment_accounts.empty:
        return pd.DataFrame(columns=["date", "balance"])

    today = pd.Timestamp.today().normalize()
    periods = pd.date_range(end=today, periods=12, freq="M")
    balances = pd.Series([investment_accounts["balance"].astype(float).sum()] * len(periods), index=periods)
    return pd.DataFrame({"date": periods, "balance": balances})


def render_benchmarking_tab(transactions: pd.DataFrame, accounts: pd.DataFrame, *, year_label: str) -> None:
    st.caption("Comparing investment balances to S&P 500 (placeholder data)")
    if accounts is None or accounts.empty:
        st.info("Upload Accounts CSV to view benchmarking.")
        return

    if str(year_label).upper() in {"ALL", ALL_YEARS_LABEL}:
        start_date, end_date = compute_date_range("ytd")
    else:
        start_date, end_date = compute_date_range("full_year", year=year_label)

    inv_df = _prepare_investment_balances(accounts)
    inv_df = filter_dataframe_by_date(inv_df, (start_date, end_date), date_column="date") if not inv_df.empty else inv_df

    if inv_df.empty:
        st.info("No investment account balances available for this range.")
        return

    sp500_series = _mock_sp500_series(inv_df["date"])
    base_balance = inv_df["balance"].iloc[0]
    normalized_inv = inv_df["balance"] / base_balance * 100
    normalized_sp = sp500_series / sp500_series.iloc[0] * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=inv_df["date"], y=normalized_inv, mode="lines", name="Investments"))
    fig.add_trace(go.Scatter(x=normalized_sp.index, y=normalized_sp, mode="lines", name="S&P 500 (stub)"))
    fig.update_layout(yaxis_title="Indexed to 100", xaxis_title="Date", legend_title="Series")
    st.plotly_chart(fig, use_container_width=True)
