# main.py (Monarch+ Personal Finance Dashboard v2)

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime as dt
from dateutil.relativedelta import relativedelta

# ------------------------------
# Session State Initialization
# ------------------------------
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}

# ------------------------------
# Helper Functions
# ------------------------------
def format_currency(value):
    if pd.isna(value):
        return "$0.00"
    return f"(${abs(value):,.2f})" if value < 0 else f"${value:,.2f}"

def load_csv(file):
    return pd.read_csv(file)

def extract_transaction_summary(transactions):
    transactions['Date'] = pd.to_datetime(transactions['Date'])
    first_date = transactions['Date'].min()
    last_date = transactions['Date'].max()
    total_income = transactions[transactions['Amount'] > 0]['Amount'].sum()
    total_expense = transactions[transactions['Amount'] < 0]['Amount'].sum()
    net_cashflow = total_income + total_expense
    return first_date, last_date, total_income, total_expense, net_cashflow

def summarize_balance_sheet(accounts_df):
    total_assets = accounts_df[accounts_df['Type'].str.lower() == 'asset']['Balance'].sum()
    total_liabilities = accounts_df[accounts_df['Type'].str.lower() == 'liability']['Balance'].sum()
    equity = total_assets - total_liabilities
    return total_assets, total_liabilities, equity

# ------------------------------
# Sidebar - General Info & User Area
# ------------------------------
st.sidebar.title("👤 User Center")
st.sidebar.markdown("Manage uploaded snapshots below:")

with st.sidebar.expander("📂 Uploaded CSV Snapshots"):
    for fname in st.session_state.uploaded_files:
        st.write(f"- {fname}")

# ------------------------------
# Top Tabs
# ------------------------------
tabs = st.tabs(["📊 Dashboard", "📁 Transactions", "📄 Insights", "📌 Loan Tracker", "📎 Loan Calculator", "💬 Assistant"])

# ------------------------------
# Dashboard Tab
# ------------------------------
with tabs[0]:
    st.header("🏠 Monarch+ Dashboard")
    uploaded_transactions = st.file_uploader("Upload Transactions CSV", type=["csv"], key="transactions")
    uploaded_accounts = st.file_uploader("Upload Accounts CSV", type=["csv"], key="accounts")

    if uploaded_transactions and uploaded_accounts:
        st.session_state.uploaded_files['Transactions'] = uploaded_transactions.name
        st.session_state.uploaded_files['Accounts'] = uploaded_accounts.name

        transactions_df = load_csv(uploaded_transactions)
        accounts_df = load_csv(uploaded_accounts)

        first_date, last_date, income, expense, net = extract_transaction_summary(transactions_df)
        total_assets, total_liabilities, total_equity = summarize_balance_sheet(accounts_df)

        st.subheader("📌 Overview Metrics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Transactions", f"{len(transactions_df):,}")
        col2.metric("First Transaction Date", first_date.strftime("%Y-%m-%d"))
        col3.metric("Last Transaction Date", last_date.strftime("%Y-%m-%d"))

        col4, col5, col6 = st.columns(3)
        col4.metric("Total Income", format_currency(income))
        col5.metric("Total Expenses", format_currency(expense))
        col6.metric("Net Cash Flow", format_currency(net))

        col7, col8, col9 = st.columns(3)
        col7.metric("Total Assets", format_currency(total_assets))
        col8.metric("Total Liabilities", format_currency(total_liabilities))
        col9.metric("Net Worth", format_currency(total_equity))

        st.markdown("---")
        st.info("You can also upload CSVs from **YNAB**, **Tiller**, **PocketSmith**, and others if formatted similarly.")

# ------------------------------
# Transactions Tab (Filters + Snapshots)
# ------------------------------
with tabs[1]:
    st.header("📁 Transaction Explorer")
    if uploaded_transactions:
        transactions_df = load_csv(uploaded_transactions)
        transactions_df['Date'] = pd.to_datetime(transactions_df['Date'])

        # Date Range Filters
        today = dt.date.today()
        presets = {
            "Year to Date": (dt.date(today.year, 1, 1), today),
            "Last 30 Days": (today - dt.timedelta(days=30), today),
            "Last 90 Days": (today - dt.timedelta(days=90), today),
            "Last Year": (today - relativedelta(years=1), today),
        }
        preset_label = st.selectbox("📆 Select Date Range Preset", options=list(presets.keys()))
        start_date, end_date = presets[preset_label]
        start_date = st.date_input("Start Date", value=start_date)
        end_date = st.date_input("End Date", value=end_date)

        filtered_df = transactions_df[(transactions_df['Date'] >= pd.to_datetime(start_date)) & (transactions_df['Date'] <= pd.to_datetime(end_date))]

        # Summary Metrics
        st.subheader("📊 Summary Metrics")
        col1, col2, col3 = st.columns(3)
        income = filtered_df[filtered_df['Amount'] > 0]['Amount'].sum()
        expense = filtered_df[filtered_df['Amount'] < 0]['Amount'].sum()
        net = income + expense
        col1.metric("Filtered Income", format_currency(income))
        col2.metric("Filtered Expenses", format_currency(expense))
        col3.metric("Filtered Net Flow", format_currency(net))

        # Monthly Cash Flow Line Chart
        st.subheader("📈 Monthly Cash Flow")
        monthly = filtered_df.copy()
        monthly['YearMonth'] = monthly['Date'].dt.to_period('M').astype(str)
        monthly_summary = monthly.groupby('YearMonth')['Amount'].sum().reset_index()
        fig = px.line(monthly_summary, x='YearMonth', y='Amount', markers=True)
        fig.update_layout(yaxis_tickformat="$,.0f", xaxis_title="Month", yaxis_title="Cash Flow ($)")
        st.plotly_chart(fig, use_container_width=True)

        # TODO: Add snapshot tables by year/month/week breakdowns

# ------------------------------
# Assistant Tab
# ------------------------------
with tabs[5]:
    st.header("💬 Chat With Your Data")
    user_prompt = st.text_input("Ask a question about your finances:")
    if user_prompt:
        st.write("(AI response would go here...)")
        # Placeholder logic
        st.success("This will later connect to ChatGPT or an LLM backend to provide insights.")

# ------------------------------
# Notes
# ------------------------------
# Tabs [2] [3] [4] to be built out incrementally as feature sets expand
# Data ingestion from other CSV types (YNAB, Tiller) will require field mapping and format detection logic





