# src/dashboard/sections/charts.py

import streamlit as st
import pandas as pd

from src.formatting import format_currency


TOP_N = 7
DEFAULT_EXCLUSIONS = ["Credit Card Payment", "Transfer"]


def _init_chart_state(key: str, default: list[str]) -> None:
    if key not in st.session_state:
        st.session_state[key] = default.copy()


def _filter_exclusions(df: pd.DataFrame, exclude: list[str]) -> pd.DataFrame:
    if not exclude:
        return df
    return df[~df["category"].isin(exclude)]


def _top_income(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[df["amount"] > 0]
        .groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .head(TOP_N)
    )


def _top_expenses(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[df["amount"] < 0]
        .assign(amount=lambda d: d["amount"].abs())
        .groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .head(TOP_N)
    )


def _most_frequent(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[df["amount"] < 0]
        .groupby("category", as_index=False)
        .size()
        .rename(columns={"size": "occurrences"})
        .sort_values("occurrences", ascending=False)
        .head(TOP_N)
    )


def render_charts_section(transactions: pd.DataFrame) -> None:
    st.markdown("## Snapshot Details")

    # -------------------------------------------------
    # Session State
    # -------------------------------------------------
    _init_chart_state("exclude_income", DEFAULT_EXCLUSIONS)
    _init_chart_state("exclude_expense", DEFAULT_EXCLUSIONS)
    _init_chart_state("exclude_frequency", DEFAULT_EXCLUSIONS)

    # -------------------------------------------------
    # Configure Section (collapsed by default)
    # -------------------------------------------------
    with st.expander("⚙️ Configure metrics per section", expanded=False):
        if st.button("Reset to Defaults"):
            st.session_state.exclude_income = DEFAULT_EXCLUSIONS.copy()
            st.session_state.exclude_expense = DEFAULT_EXCLUSIONS.copy()
            st.session_state.exclude_frequency = DEFAULT_EXCLUSIONS.copy()

        st.multiselect(
            "Income",
            options=sorted(transactions["category"].unique()),
            default=st.session_state.exclude_income,
            key="exclude_income",
        )

        st.multiselect(
            "Expenses",
            options=sorted(transactions["category"].unique()),
            default=st.session_state.exclude_expense,
            key="exclude_expense",
        )

        st.multiselect(
            "Most Frequent Expenses",
            options=sorted(transactions["category"].unique()),
            default=st.session_state.exclude_frequency,
            key="exclude_frequency",
        )

        st.caption("Exclusions persist across date ranges until manually cleared.")

    # -------------------------------------------------
    # Prepare Data
    # -------------------------------------------------
    income_df = _top_income(
        _filter_exclusions(transactions, st.session_state.exclude_income)
    )

    expense_df = _top_expenses(
        _filter_exclusions(transactions, st.session_state.exclude_expense)
    )

    freq_df = _most_frequent(
        _filter_exclusions(transactions, st.session_state.exclude_frequency)
    )

    # -------------------------------------------------
    # Charts
    # -------------------------------------------------
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### Top Income Sources")
        st.bar_chart(
            income_df.set_index("category")["amount"],
            height=280,
        )

        with st.expander("Show income totals"):
            for _, r in income_df.iterrows():
                st.write(f"{r['category']}: {format_currency(r['amount'])}")

    with c2:
        st.markdown("### Top Expenses")
        st.bar_chart(
            expense_df.set_index("category")["amount"],
            height=280,
        )

        with st.expander("Show expense totals"):
            for _, r in expense_df.iterrows():
                st.write(f"{r['category']}: {format_currency(r['amount'])}")

    with c3:
        st.markdown("### Most Frequent Expenses")
        st.bar_chart(
            freq_df.set_index("category")["occurrences"],
            height=280,
        )

        with st.expander("Show frequency totals"):
            for _, r in freq_df.iterrows():
                st.write(f"{r['category']}: {r['occurrences']}")
