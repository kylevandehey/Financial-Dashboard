import streamlit as st
import altair as alt
import pandas as pd
from src.formatting import format_currency


def render_expense_chart(transactions, selected_categories):
    if transactions.empty:
        return

    df = transactions.copy()
    df = df[df["amount"] < 0]

    grouped = (
        df.groupby("category")["amount"]
        .sum()
        .abs()
        .sort_values(ascending=False)
        .head(7)
        .reset_index()
    )

    if selected_categories:
        grouped = grouped[grouped["category"].isin(selected_categories)]

    grouped["amount_fmt"] = grouped["amount"].apply(format_currency)

    st.markdown("### Top Expenses")

    chart = (
        alt.Chart(grouped)
        .mark_bar()
        .encode(
            x=alt.X("category:N", sort="-y", title="Category"),
            y=alt.Y("amount:Q", title="Expense"),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("amount_fmt:N", title="Total"),
            ],
        )
        .properties(height=300)
    )

    st.altair_chart(chart, use_container_width=True)

    with st.expander("Show expense totals"):
        st.dataframe(grouped, use_container_width=True)
