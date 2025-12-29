# main.py — Monarch+ Dashboard (Full Feature Build)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import altair as alt
import hashlib
from datetime import datetime
from sklearn.metrics import pairwise_distances_argmin_min
from dateutil import parser
from streamlit_extras.metric_cards import style_metric_cards

# -------------------------------
# SESSION STATE INIT
# -------------------------------
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# -------------------------------
# AUTHENTICATION LAYER (SIMPLE)
# -------------------------------
def login():
    with st.sidebar:
        st.markdown("### 🔐 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username == "demo" and password == "pass":
                st.session_state.authenticated = True
            else:
                st.error("Invalid credentials")

def hash_string(s):
    return hashlib.sha256(s.encode()).hexdigest()

if not st.session_state.authenticated:
    login()
    st.stop()

# -------------------------------
# LOAD CSVs
# -------------------------------
def load_csv(file):
    try:
        return pd.read_csv(file)
    except Exception:
        return pd.DataFrame()

def summarize_balance_sheet(df):
    try:
        df.columns = df.columns.str.strip().str.lower()
        assets = df[df['type'].str.lower() == 'asset']['balance'].sum()
        liabilities = df[df['type'].str.lower() == 'liability']['balance'].sum()
        equity = df[df['type'].str.lower() == 'equity']['balance'].sum()
        return assets, liabilities, equity
    except:
        return 0, 0, 0

@st.cache_data

def detect_recurring(df, col='Description'):
    df['Recurring'] = df[col].duplicated(keep=False)
    return df

# -------------------------------
# DASHBOARD STARTS
# -------------------------------
st.set_page_config("Monarch+ Dashboard", layout="wide")
st.title("🏠 Monarch+ Dashboard")

# -------------------------------
# Uploads
# -------------------------------
transactions_file = st.file_uploader("Upload Transactions CSV", type="csv", key="trans")
accounts_file = st.file_uploader("Upload Accounts CSV", type="csv", key="acc")

if transactions_file:
    transactions_df = load_csv(transactions_file)
    transactions_df.columns = transactions_df.columns.str.strip().str.lower()
    transactions_df['date'] = pd.to_datetime(transactions_df['date'], errors='coerce')
    transactions_df = transactions_df.dropna(subset=['date'])
    transactions_df['amount'] = pd.to_numeric(transactions_df['amount'], errors='coerce')
    start_date, end_date = transactions_df['date'].min(), transactions_df['date'].max()
else:
    transactions_df = pd.DataFrame()
    start_date, end_date = None, None

if accounts_file:
    accounts_df = load_csv(accounts_file)
    accounts_df.columns = accounts_df.columns.str.strip().str.lower()
    total_assets, total_liabilities, total_equity = summarize_balance_sheet(accounts_df)
else:
    accounts_df = pd.DataFrame()
    total_assets, total_liabilities, total_equity = 0, 0, 0

# -------------------------------
# Dashboard Metrics
# -------------------------------
if not transactions_df.empty:
    total_income = transactions_df[transactions_df['amount'] > 0]['amount'].sum()
    total_expense = transactions_df[transactions_df['amount'] < 0]['amount'].sum()
    net_cashflow = total_income + total_expense
    st.subheader("📊 Key Financial Metrics")
    style_metric_cards()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Transactions", f"{len(transactions_df):,}")
    col2.metric("Date Range", f"{start_date.date()} → {end_date.date()}")
    col3.metric("Total Income", f"${total_income:,.2f}")
    col4.metric("Total Expenses", f"(${abs(total_expense):,.2f})")
    col5.metric("Net Cash Flow", f"${net_cashflow:,.2f}")
    st.divider()

    colA, colB, colC = st.columns(3)
    colA.metric("Total Assets", f"${total_assets:,.0f}")
    colB.metric("Liabilities", f"(${abs(total_liabilities):,.0f})")
    colC.metric("Equity", f"${total_equity:,.0f}")

# -------------------------------
# Insights Tab (Recurring + Charts)
# -------------------------------
if not transactions_df.empty:
    st.header("📈 Insights")
    with st.expander("💸 Monthly Cash Flow Chart"):
        monthly = transactions_df.groupby(pd.Grouper(key='date', freq='M'))['amount'].sum().reset_index()
        monthly['month'] = monthly['date'].dt.strftime('%b %Y')
        fig = px.bar(monthly, x='month', y='amount', title='Monthly Net Cash Flow', labels={'amount': 'Net Flow'})
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔁 Recurring Expense Detection"):
        transactions_df = detect_recurring(transactions_df)
        st.dataframe(transactions_df[transactions_df['recurring']])

# -------------------------------
# Assistant Placeholder
# -------------------------------
with st.sidebar:
    st.markdown("## 🤖 Assistant")
    st.markdown("This section will include natural language chat with financial data context.")

# -------------------------------
# Year Tabs (if requested)
# -------------------------------
if not transactions_df.empty:
    years = sorted(transactions_df['date'].dt.year.unique())
    selected_year = st.selectbox("Select Year to View", years[::-1])
    df_year = transactions_df[transactions_df['date'].dt.year == selected_year]
    st.subheader(f"🗓️ {selected_year} Summary")
    st.write(df_year.describe())
    st.dataframe(df_year)

# -------------------------------
# Login Sidebar Info
# -------------------------------
with st.sidebar:
    st.markdown("---")
    st.markdown("👤 Logged in as: `demo`")
    if transactions_file:
        st.markdown(f"🗂 Uploaded Transactions Snapshot: `{transactions_file.name}`")
    if accounts_file:
        st.markdown(f"💼 Uploaded Account Balances: `{accounts_file.name}`")

# -------------------------------
# Footer
# -------------------------------
st.markdown("---")
st.caption("Monarch+ Dashboard · Built with ❤️ by Authentic Financial")






