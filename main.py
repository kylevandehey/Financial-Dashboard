import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt

st.set_page_config(page_title="Monarch+ Personal Finance Dashboard", layout="wide")

# ---------- Sidebar Upload Section ----------
st.sidebar.title("📁 Data Manager")
st.sidebar.markdown("**Upload trade-log CSV**")
st.sidebar.file_uploader("Drag and drop file here", type="csv")
st.sidebar.markdown("✅ Supports Monarch, Tiller, YNAB, PocketSmith, and more.")

# ---------- Tabs ----------
tabs = st.tabs(["📊 Dashboard", "💰 Transactions", "🏦 Accounts", "🧠 Insights", "📈 Loans", "🧮 Loan Calculator", "💬 Assistant"])

df_txn, df_accounts = None, None

# ---------- Dashboard Tab ----------
with tabs[0]:
    st.header("📊 Dashboard")

    st.subheader("📥 Upload Your Files")
    col1, col2 = st.columns(2)
    with col1:
        txn_file = st.file_uploader("Upload Transactions CSV", type="csv", key="txn")
    with col2:
        acct_file = st.file_uploader("Upload Accounts CSV", type="csv", key="acct")

    if txn_file:
        df_txn = pd.read_csv(txn_file)
        df_txn['Date'] = pd.to_datetime(df_txn['Date'])

    if acct_file:
        df_accounts = pd.read_csv(acct_file)
        if 'Date' in df_accounts.columns:
            df_accounts['Date'] = pd.to_datetime(df_accounts['Date'])

    # Date Range Filters
    st.subheader("📆 Date Range Filters")
    preset_options = {
        "Year to Date": (dt.date(dt.datetime.now().year, 1, 1), dt.date.today()),
        "Last 12 Months": (dt.date.today() - pd.DateOffset(months=12), dt.date.today()),
        "Last 30 Days": (dt.date.today() - pd.DateOffset(days=30), dt.date.today()),
        "All Time": (None, None),
    }

    preset = st.selectbox("Preset Ranges", list(preset_options.keys()), index=0)
    if preset_options[preset][0] is not None:
        start_date, end_date = preset_options[preset]
    else:
        start_date, end_date = None, None

    col1, col2 = st.columns(2)
    with col1:
        custom_start = st.date_input("Start Date", start_date)
    with col2:
        custom_end = st.date_input("End Date", end_date)

    if df_txn is not None:
        df_txn = df_txn[(df_txn['Date'] >= pd.to_datetime(custom_start)) & (df_txn['Date'] <= pd.to_datetime(custom_end))]

        st.success(f"{len(df_txn)} transactions loaded!")

        # High-level summary metrics
        col1, col2, col3 = st.columns(3)
        total_income = df_txn[df_txn['Amount'] > 0]['Amount'].sum()
        total_expense = df_txn[df_txn['Amount'] < 0]['Amount'].sum()
        net_cashflow = total_income + total_expense

        col1.metric("Total Income", f"${total_income:,.2f}")
        col2.metric("Total Expenses", f"${total_expense:,.2f}")
        col3.metric("Net Cash Flow", f"${net_cashflow:,.2f}")

        st.subheader("📈 Monthly Cash Flow")
        monthly = df_txn.groupby(df_txn['Date'].dt.to_period('M'))['Amount'].sum()
        st.line_chart(monthly)

        st.subheader("📊 Spending by Category")
        cat_group = df_txn.groupby('Category')['Amount'].sum().sort_values()
        st.bar_chart(cat_group)

        # Summary metric boxes by top 5 categories (income & expenses)
        st.subheader("💼 Top Categories Summary")
        income_cats = df_txn[df_txn['Amount'] > 0].groupby('Category')['Amount'].sum().sort_values(ascending=False)
        expense_cats = df_txn[df_txn['Amount'] < 0].groupby('Category')['Amount'].sum().sort_values()

        st.markdown("#### 🟢 Top Income Categories")
        show_all_income = st.toggle("Show All Income Categories")
        income_display = income_cats if show_all_income else income_cats.head(5)
        for cat, amt in income_display.items():
            st.metric(label=cat, value=f"${amt:,.2f}")

        st.markdown("#### 🔴 Top Expense Categories")
        show_all_expense = st.toggle("Show All Expense Categories")
        expense_display = expense_cats if show_all_expense else expense_cats.head(5)
        for cat, amt in expense_display.items():
            st.metric(label=cat, value=f"${amt:,.2f}")

    if df_accounts is not None:
        st.subheader("📦 Net Worth Snapshot")
        if {'Asset', 'Liability'}.issubset(df_accounts.columns):
            asset_total = df_accounts['Asset'].sum()
            liability_total = df_accounts['Liability'].sum()
            equity = asset_total - liability_total

            st.metric("Total Assets", f"${asset_total:,.2f}")
            st.metric("Total Liabilities", f"${liability_total:,.2f}")
            st.metric("Net Worth", f"${equity:,.2f}")

# ---------- Transactions Tab ----------
with tabs[1]:
    st.header("📄 All Transactions")
    if df_txn is not None:
        st.dataframe(df_txn.sort_values("Date", ascending=False))

# ---------- Accounts Tab ----------
with tabs[2]:
    st.header("🏦 Account Balance Over Time")
    if df_accounts is not None:
        df_accounts['Date'] = pd.to_datetime(df_accounts['Date'])
        if {'Date', 'Amount'}.issubset(df_accounts.columns):
            trend = df_accounts.groupby('Date')['Amount'].sum().reset_index()
            st.line_chart(trend.set_index('Date'))

# ---------- Insights Tab (Placeholder) ----------
with tabs[3]:
    st.header("🧠 Financial Health Insights")
    st.markdown("- Coming soon: volatility scores, savings rate, debt ratios, tax readiness, trailing averages")

# ---------- Loans Tab (Placeholder) ----------
with tabs[4]:
    st.header("📈 Loan Planning & Amortization")
    st.markdown("- Future: Add mortgage, vehicle, student loans and visualize payoff strategies.")

# ---------- Loan Calculator ----------
with tabs[5]:
    st.header("🧮 Loan Calculator")
    loan_amt = st.number_input("Loan Amount", value=25000)
    interest = st.number_input("Annual Interest Rate (%)", value=5.0)
    years = st.number_input("Loan Term (Years)", value=5)

    months = years * 12
    monthly_rate = interest / 100 / 12
    payment = loan_amt * monthly_rate / (1 - (1 + monthly_rate) ** -months)

    st.metric("Monthly Payment", f"${payment:,.2f}")

# ---------- Assistant Tab ----------
with tabs[6]:
    st.header("💬 Ask a Financial Question")
    query = st.text_area("What do you want to know about your finances?")
    if query:
        st.info("This feature will soon connect to a financial GPT assistant.")



