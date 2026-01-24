import streamlit as st
import altair as alt
import pandas as pd


def render_frequency_chart(transactions, selected_categories):
    if transactions.empty:
        return

    df = transactions.copy()
    df = df[df["amount"] < 0]

    grouped = (
        df.groupby("category")
        .size()
        .sort_values(ascending=False)
        .head(7)
        .reset_index(name="count")
    )

    if selected_categories:
        grouped = grouped[grouped["category"].isin(selected_categories)]

    st.markdown("### Most Frequent Expenses")

    chart = (
        alt.Chart(grouped)
        .mark_bar()
        .encode(
            x=alt.X("category:N", sort="-y", title="Category"),
            y=alt.Y("count:Q", title="Occurrences"),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("count:Q", title="Occurrences"),
            ],
        )
        .properties(height=300)
    )

    st.altair_chart(chart, use_container_width=True)

    with st.expander("Show frequency table"):
        st.dataframe(grouped, use_container_width=True)
