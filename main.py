import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# -----------------------------
# Placeholder: Optional Auth UI (not enforced)
# -----------------------------
st.sidebar.subheader("🔐 User Login (Coming Soon)")
st.sidebar.text_input("Username", disabled=True)
st.sidebar.text_input("Password", type="password", disabled=True)
st.sidebar.markdown("<i>Authentication not required yet.</i>", unsafe_allow_html=True)

# -----------------------------
# Session State Initialization
# -----------------------------
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}

# -----------------------------
# App Title & Tabs
# -----------------------------
st.set_page_config(layout="wide")
st.title("📊 Monarch+ Dashboard")
tabs = st.tabs(["Dashboard", "Transactions", "Insights", "Loan Tracker", "Loan Calculator", "Assistant"])

# -----------------------------
# File Uploads (Dashboard Tab)
# -----------------------------
with tabs[0]:
    st.subheader("Upload Transactions CSV")
    transactions_file = st.file_uploader("Upload transactions CSV", type="csv", key="transactions")

    st.subheader("Upload Accounts CSV")
    accounts_file = st.file_uploader("Upload accounts/balances CSV", type="csv", key="accounts")

    if transactions_file:
        transactions_df = pd.read_csv(transactions_file)
        st.session_state.uploaded_files['transactions'] = transactions_df

    if accounts_file:
        accounts_df = pd.read_csv(accounts_file)
        st.session_state.uploaded_files['accounts'] = accounts_df

    # Show metadata insights (only if uploaded)
    if 'transactions' in st.session_state.uploaded_files:
        df = st.session_state.uploaded_files['transactions']
        st.markdown("### 📅 High-Level Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Transactions", len(df))
        with col2:
            st.metric("First Transaction", df['Date'].min())
        with col3:
            st.metric("Last Transaction", df['Date'].max())

    if 'accounts' in st.session_state.uploaded_files:
        acc = st.session_state.uploaded_files['accounts']
        if 'Type' in acc.columns and 'Balance' in acc.columns:
            total_assets = acc[acc['Type'].str.lower() == 'asset']['Balance'].sum()
            total_liabilities = acc[acc['Type'].str.lower() == 'liability']['Balance'].sum()
            total_equity = total_assets - total_liabilities
            st.markdown("### 💰 Balance Sheet Snapshot")
            col1, col2, col3 = st.columns(3)
            col1.metric("Assets", f"${total_assets:,.2f}")
            col2.metric("Liabilities", f"${total_liabilities:,.2f}")
            col3.metric("Equity", f"${total_equity:,.2f}")
        else:
            st.warning("⚠️ Account CSV missing required columns: 'Type', 'Balance'")

# -----------------------------
# Transactions Tab: Filters + Summaries
# -----------------------------
with tabs[1]:
    st.subheader("📂 Transactions Explorer")

    if 'transactions' in st.session_state.uploaded_files:
        df = st.session_state.uploaded_files['transactions']

        # Format date column if needed
        if not pd.api.types.is_datetime64_any_dtype(df['Date']):
            df['Date'] = pd.to_datetime(df['Date'])

        # Year filter
        year_list = sorted(df['Date'].dt.year.unique(), reverse=True)
        selected_year = st.selectbox("Filter by Year", options=year_list, index=0)
        df_filtered = df[df['Date'].dt.year == selected_year]

        # Snapshot Metrics
        st.markdown(f"### Summary for {selected_year}")
        income = df_filtered[df_filtered['Amount'] > 0]['Amount'].sum()
        expense = df_filtered[df_filtered['Amount'] < 0]['Amount'].sum()
        net_cashflow = income + expense
        col1, col2, col3 = st.columns(3)
        col1.metric("Income", f"${income:,.2f}")
        col2.metric("Expenses", f"(${abs(expense):,.2f})")
        col3.metric("Net Cashflow", f"${net_cashflow:,.2f}")

        # Monthly Cashflow Chart
        st.markdown("### 📈 Monthly Cash Flow")
        monthly_cf = df_filtered.groupby(df_filtered['Date'].dt.to_period("M"))['Amount'].sum().reset_index()
        monthly_cf['Date'] = monthly_cf['Date'].dt.to_timestamp()
        fig = px.bar(monthly_cf, x='Date', y='Amount', title='Monthly Net Flow')
        st.plotly_chart(fig, use_container_width=True)

        # Recurring Expense Detection
        st.markdown("### 🔁 Potential Recurring Expenses")
        recurring = df_filtered[df_filtered['Amount'] < 0]
        recurring_summary = recurring.groupby('Description').filter(lambda x: len(x) > 3)
        if not recurring_summary.empty:
            recurring_grouped = recurring_summary.groupby('Description')['Amount'].agg(['count', 'mean', 'sum'])
            st.dataframe(recurring_grouped.sort_values(by='count', ascending=False))
        else:
            st.info("No recurring expenses found with >3 entries")

        # Full Table View
        with st.expander("🔍 View Raw Transactions"):
            st.dataframe(df_filtered)

    else:
        st.info("Upload a transactions CSV to view data.")

# -----------------------------
# Assistant (Placeholder)
# -----------------------------
with tabs[5]:
    st.subheader("🧠 Ask the Assistant")
    st.markdown("This is where your AI assistant will go once integrated with OpenAI's API.")
    st.text_area("Ask a question about your finances...")
    st.button("Submit (Coming Soon)")







