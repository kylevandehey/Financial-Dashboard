import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Monarch Money Dashboard", layout="wide")

st.title("📊 Monarch Money Dashboard")

# Upload section
uploaded_file = st.file_uploader("Upload your Monarch transactions CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df['Date'] = pd.to_datetime(df['Date'])

    # Clean columns (adjust if needed)
    df.columns = [col.strip() for col in df.columns]

    st.success(f"{len(df)} transactions loaded!")

    # Metrics
    income = df[df['Amount'] > 0]['Amount'].sum()
    expenses = df[df['Amount'] < 0]['Amount'].sum()
    cash_flow = income + expenses

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"${income:,.2f}")
    col2.metric("Total Expenses", f"${expenses:,.2f}")
    col3.metric("Net Cash Flow", f"${cash_flow:,.2f}")

    # Monthly Cash Flow
    df['Month'] = df['Date'].dt.to_period('M')
    monthly_cf = df.groupby('Month')['Amount'].sum().reset_index()
    monthly_cf['Month'] = monthly_cf['Month'].astype(str)

    st.subheader("\ud83d\udcc8 Monthly Cash Flow")
    st.line_chart(monthly_cf.set_index('Month')['Amount'])

    # Category breakdown
    if 'Category' in df.columns:
        st.subheader("\ud83e\uddfe Spending by Category")
        category_totals = df[df['Amount'] < 0].groupby('Category')['Amount'].sum().sort_values()
        st.bar_chart(category_totals)

    # Show full table
    st.subheader("\ud83d\uddc3\ufe0f All Transactions")
    st.dataframe(df.sort_values('Date', ascending=False))
else:
    st.info("Upload a CSV file to get started.")
