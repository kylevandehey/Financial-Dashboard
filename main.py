# main.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from datetime import datetime

# App config
st.set_page_config(layout="wide", page_title="Monarch+ Dashboard")

# Session state init
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}

# Placeholder login panel
with st.sidebar:
    st.markdown("#### 🔒 User Login (Coming Soon)")
    st.text_input("Username")
    st.text_input("Password", type="password")
    st.caption("Authentication not required yet.")

# Tabs (top navigation layout)
tabs = st.tabs(["🏠 Dashboard", "📄 Transactions", "📊 Insights", "📈 Loan Tracker", "🧮 Loan Calculator", "💬 Assistant"])

### --- TAB 1: DASHBOARD --- ###
with tabs[0]:
    st.title("Monarch+ Dashboard")

    st.subheader("Upload Transactions CSV")
    transactions_file = st.file_uploader("Upload Transactions File", type="csv", key="transactions")

    st.subheader("Upload Accounts CSV")
    accounts_file = st.file_uploader("Upload Accounts File", type="csv", key="accounts")

    if transactions_file and accounts_file:
        transactions_df = pd.read_csv(transactions_file)
        accounts_df = pd.read_csv(accounts_file)

        # Auto-detect and convert date column
        if 'Date' in transactions_df.columns:
            transactions_df['Date'] = pd.to_datetime(transactions_df['Date'], errors='coerce')

        if 'Type' in accounts_df.columns and 'Balance' in accounts_df.columns:
            accounts_df['Type'] = accounts_df['Type'].str.lower()
            total_assets = accounts_df[accounts_df['Type'] == 'asset']['Balance'].sum()
            total_liabilities = accounts_df[accounts_df['Type'] == 'liability']['Balance'].sum()
            total_equity = total_assets - total_liabilities

            st.metric("Total Assets", f"${total_assets:,.2f}")
            st.metric("Total Liabilities", f"${total_liabilities:,.2f}")
            st.metric("Equity", f"${total_equity:,.2f}")
        else:
            st.error("Ensure 'Type' and 'Balance' columns exist in Accounts file.")

        # Date filter
        with st.expander("📅 Filter Date Range"):
            start_date = st.date_input("Start Date", value=transactions_df['Date'].min().date())
            end_date = st.date_input("End Date", value=transactions_df['Date'].max().date())

        def filter_by_date(df, start_date, end_date):
            df = df[df['Date'].notnull()]  # ensure no NaT
            return df[(df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))]

        filtered_df = filter_by_date(transactions_df, start_date, end_date)

        st.subheader("💰 Summary Metrics")
        st.metric("Income", f"${filtered_df[filtered_df['Amount'] > 0]['Amount'].sum():,.2f}")
        st.metric("Expenses", f"${-filtered_df[filtered_df['Amount'] < 0]['Amount'].sum():,.2f}")
        st.metric("Net", f"${filtered_df['Amount'].sum():,.2f}")

    else:
        st.warning("Please upload both Transactions and Accounts CSV files.")

### --- TAB 2: TRANSACTIONS --- ###
with tabs[1]:
    st.header("📄 Transactions Viewer")
    if transactions_file:
        st.dataframe(transactions_df)
    else:
        st.info("Upload a Transactions file in the Dashboard tab.")

### --- TAB 3: INSIGHTS --- ###
with tabs[2]:
    st.header("📊 Financial Insights")
    if transactions_file:
        st.subheader("Toggle Chart View")
        chart_type = st.selectbox("Chart Type", ["Bar Chart", "Line Chart", "Pie Chart"])

        category_grouped = filtered_df.groupby('Category')['Amount'].sum().sort_values()

        if chart_type == "Bar Chart":
            fig = px.bar(category_grouped, x=category_grouped.index, y=category_grouped.values, labels={'x':'Category', 'y':'Amount'})
            st.plotly_chart(fig)
        elif chart_type == "Pie Chart":
            fig = px.pie(names=category_grouped.index, values=category_grouped.values)
            st.plotly_chart(fig)
        else:
            fig = px.line(filtered_df.sort_values('Date'), x='Date', y='Amount', color='Category')
            st.plotly_chart(fig)
    else:
        st.info("Upload data first in the Dashboard tab.")

### --- TAB 4: LOAN TRACKER --- ###
with tabs[3]:
    st.header("📈 Loan Tracker")
    st.info("Coming soon — amortization tracking and payoff planning.")

### --- TAB 5: LOAN CALCULATOR --- ###
with tabs[4]:
    st.header("🧮 Loan Calculator")
    loan_amount = st.number_input("Loan Amount", value=10000)
    interest_rate = st.number_input("Interest Rate (%)", value=5.0)
    loan_term = st.number_input("Term (years)", value=5)

    if loan_amount > 0 and interest_rate > 0 and loan_term > 0:
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term * 12
        monthly_payment = loan_amount * monthly_rate / (1 - (1 + monthly_rate)**-num_payments)
        st.metric("Monthly Payment", f"${monthly_payment:,.2f}")

### --- TAB 6: ASSISTANT --- ###
with tabs[5]:
    st.header("💬 AI Assistant")
    st.info("Assistant functionality will be integrated here. Use this space to ask about your finances.")









