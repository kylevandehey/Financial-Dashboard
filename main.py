import streamlit as st
st.set_page_config(layout="wide", page_title="Monarch+ Dashboard")

import pandas as pd
import numpy as np
import plotly.express as px
import os
import base64
from datetime import datetime
from io import StringIO

# -----------------------------
# Utility Functions
# -----------------------------
def load_csv(uploaded_file):
    try:
        return pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Failed to load file: {e}")
        return pd.DataFrame()

def summarize_balance_sheet(accounts_df):
    if 'Type' not in accounts_df.columns or 'Balance' not in accounts_df.columns:
        return 0, 0, 0
    accounts_df['Type'] = accounts_df['Type'].str.lower()
    total_assets = accounts_df[accounts_df['Type'] == 'asset']['Balance'].sum()
    total_liabilities = accounts_df[accounts_df['Type'] == 'liability']['Balance'].sum()
    total_equity = total_assets - total_liabilities
    return total_assets, total_liabilities, total_equity

def summarize_transactions(trans_df):
    income = trans_df[trans_df['Amount'] > 0]['Amount'].sum()
    expenses = trans_df[trans_df['Amount'] < 0]['Amount'].sum()
    net = income + expenses
    return income, abs(expenses), net

def detect_recurring_expenses(trans_df):
    recurring = trans_df.groupby(['Description', trans_df['Date'].str[:7]]).size()
    recurring = recurring[recurring >= 2].reset_index().groupby('Description').size()
    return recurring[recurring >= 2].index.tolist()

def filter_by_date(df, start_date, end_date):
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

# -----------------------------
# Session State Initialization
# -----------------------------
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}

# -----------------------------
# Sidebar Navigation
# -----------------------------
st.sidebar.title("🔐 User Login (Coming Soon)")
st.sidebar.text_input("Username")
st.sidebar.text_input("Password", type="password")
st.sidebar.caption("Authentication not required yet.")

page = st.sidebar.radio("Navigate", ["Dashboard", "Transactions", "Insights", "Loan Tracker", "Loan Calculator", "Assistant"])

# -----------------------------
# Dashboard
# -----------------------------
if page == "Dashboard":
    st.title("🏠 Monarch+ Dashboard")

    st.subheader("Upload Transactions CSV")
    trans_file = st.file_uploader("Upload Transactions", type="csv", key="trans")
    if trans_file:
        trans_df = load_csv(trans_file)
        st.session_state.uploaded_files['transactions'] = trans_df

    st.subheader("Upload Accounts CSV")
    acc_file = st.file_uploader("Upload Accounts", type="csv", key="acc")
    if acc_file:
        acc_df = load_csv(acc_file)
        st.session_state.uploaded_files['accounts'] = acc_df

    # Date Filters
    if 'transactions' in st.session_state.uploaded_files:
        df = st.session_state.uploaded_files['transactions']
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        min_date = df['Date'].min()
        max_date = df['Date'].max()

        start_date = st.date_input("Start Date", min_value=min_date, max_value=max_date, value=min_date)
        end_date = st.date_input("End Date", min_value=min_date, max_value=max_date, value=max_date)

        filtered_df = filter_by_date(df, start_date, end_date)

        income, expenses, net = summarize_transactions(filtered_df)

        col1, col2, col3 = st.columns(3)
        col1.metric("Income", f"${income:,.2f}")
        col2.metric("Expenses", f"${expenses:,.2f}")
        col3.metric("Net", f"${net:,.2f}", delta=f"{(income - expenses):,.2f}")

    if 'accounts' in st.session_state.uploaded_files:
        acc_df = st.session_state.uploaded_files['accounts']
        total_assets, total_liabilities, total_equity = summarize_balance_sheet(acc_df)
        col1, col2, col3 = st.columns(3)
        col1.metric("Assets", f"${total_assets:,.2f}")
        col2.metric("Liabilities", f"${total_liabilities:,.2f}")
        col3.metric("Equity", f"${total_equity:,.2f}")

# -----------------------------
# Transactions Tab
# -----------------------------
elif page == "Transactions":
    st.title("📄 Transactions")
    if 'transactions' in st.session_state.uploaded_files:
        df = st.session_state.uploaded_files['transactions']
        st.dataframe(df)
        recurring = detect_recurring_expenses(df)
        if recurring:
            st.subheader("🔁 Potential Recurring Expenses")
            st.write(recurring)

# -----------------------------
# Insights Tab (Stub)
# -----------------------------
elif page == "Insights":
    st.title("📊 Financial Insights")
    st.info("More insights and charting features coming soon!")

# -----------------------------
# Loan Tracker Tab (Stub)
# -----------------------------
elif page == "Loan Tracker":
    st.title("🏦 Loan Tracker")
    st.warning("Loan tracking features under construction.")

# -----------------------------
# Loan Calculator Tab (Stub)
# -----------------------------
elif page == "Loan Calculator":
    st.title("🧮 Loan Calculator")
    st.info("Custom amortization and loan payoff calculators coming soon.")

# -----------------------------
# Assistant Tab (Stub)
# -----------------------------
elif page == "Assistant":
    st.title("🤖 Chat Assistant")
    st.success("Chat module for questions about your finances launching soon!")








