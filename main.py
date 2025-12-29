import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt

st.set_page_config(page_title="Monarch+ Personal Finance Dashboard", layout="wide")

st.title("📊 Monarch+ Personal Finance Dashboard")

# -----------------------
# SIDEBAR - Global Filters
# -----------------------
st.sidebar.header("📅 Date Range Filter")
today = dt.date.today()
start_default = dt.date(today.year, 1, 1)
end_default = today

date_range = st.sidebar.date_input("Select custom date range:", value=(start_default, end_default))
start_date, end_date = date_range

# -----------------------
# TABS
# -----------------------
tab1, tab2, tab3, tab4 = st.tabs(["💳 Transactions", "💰 Accounts", "📊 Insights", "📄 PDF Report"])

# -----------------------
# TRANSACTIONS TAB
# -----------------------
with tab1:
    st.header("💳 Upload Transactions CSV")
    txn_file = st.file_uploader("Upload Monarch Transactions CSV", type="csv", key="txn")

    if txn_file:
        df_txn = pd.read_csv(txn_file)
        df_txn.columns = [col.strip() for col in df_txn.columns]
        df_txn['Date'] = pd.to_datetime(df_txn['Date'])
        df_txn = df_txn[(df_txn['Date'].dt.date >= start_date) & (df_txn['Date'].dt.date <= end_date)]

        st.success(f"{len(df_txn)} transactions loaded for selected date range!")

        income_total = df_txn[df_txn['Amount'] > 0]['Amount'].sum()
        expense_total = df_txn[df_txn['Amount'] < 0]['Amount'].sum()
        net_total = income_total + expense_total

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"${income_total:,.2f}")
        col2.metric("Total Expenses", f"${expense_total:,.2f}")
        col3.metric("Net Cash Flow", f"${net_total:,.2f}")

        # ---------- CATEGORY METRICS ----------
        st.subheader("🧾 Top Spending & Income Categories")

        # EXPENSES
        expense_df = df_txn[df_txn['Amount'] < 0]
        expense_summary = expense_df.groupby('Category')['Amount'].sum().sort_values().reset_index()
        expense_summary['Amount'] = expense_summary['Amount'].abs()

        show_all_exp = st.toggle("Show all expense categories", value=False, key="exp_toggle")
        display_exp = expense_summary if show_all_exp else expense_summary.head(5)

        st.markdown("**💸 Expense Categories**")
        for i, row in display_exp.iterrows():
            st.metric(label=row['Category'], value=f"-${row['Amount']:,.2f}")

        # INCOME
        income_df = df_txn[df_txn['Amount'] > 0]
        income_summary = income_df.groupby('Category')['Amount'].sum().sort_values(ascending=False).reset_index()

        show_all_inc = st.toggle("Show all income categories", value=False, key="inc_toggle")
        display_inc = income_summary if show_all_inc else income_summary.head(5)

        st.markdown("**💵 Income Categories**")
        for i, row in display_inc.iterrows():
            st.metric(label=row['Category'], value=f"${row['Amount']:,.2f}")

        # VIEW AS TABLE (optional)
        if st.checkbox("Show Category Totals as Table"):
            colA, colB = st.columns(2)
            colA.dataframe(expense_summary.rename(columns={"Amount": "Spent ($)"}))
            colB.dataframe(income_summary.rename(columns={"Amount": "Earned ($)"}))

        # ---------- FULL TRANSACTIONS ----------
        st.subheader("📃 All Transactions")
        st.dataframe(df_txn.sort_values('Date', ascending=False))

    else:
        st.info("Upload a CSV file to get started.")

# -----------------------
# ACCOUNTS TAB
# -----------------------
with tab2:
    st.header("📥 Upload Accounts CSV")
    acct_file = st.file_uploader("Upload Monarch Accounts CSV (Net Worth)", type="csv", key="acct")

    if acct_file:
        df_acct = pd.read_csv(acct_file)
        df_acct.columns = [col.strip() for col in df_acct.columns]
        df_acct['Date'] = pd.to_datetime(df_acct['Date'])

        df_acct = df_acct[(df_acct['Date'].dt.date >= start_date) & (df_acct['Date'].dt.date <= end_date)]

        st.success(f"{len(df_acct)} account snapshots loaded!")

        if {'Amount', 'Date'}.issubset(df_acct.columns):
            net_worth = df_acct.groupby('Date')['Amount'].sum().reset_index()
            st.subheader("📈 Net Worth Over Time")
            st.line_chart(net_worth.set_index('Date'))

            nw_change = net_worth['Amount'].iloc[-1] - net_worth['Amount'].iloc[0]
            st.metric("Change in Net Worth", f"${nw_change:,.2f}")
        else:
            st.warning("Missing columns 'Date' and 'Amount'.")

# -----------------------
# INSIGHTS TAB
# -----------------------
with tab3:
    st.header("📊 Insights Coming Soon")
    st.info("Advanced analytics, trends, and projections will be available here.")

# -----------------------
# PDF EXPORT TAB
# -----------------------
with tab4:
    st.header("📄 PDF Report Export")
    st.info("You'll soon be able to export a PDF summary of your dashboard!")


