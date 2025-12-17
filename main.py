import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Monarch+ Personal Finance Dashboard", layout="wide")
st.title("📊 Monarch+ Personal Finance Dashboard")

tab1, tab2, tab3, tab4 = st.tabs(["💳 Transactions", "💰 Accounts", "📊 Insights", "📄 PDF Report"])

# ---------------------- TRANSACTIONS TAB ----------------------
with tab1:
    st.header("💳 Upload Transactions CSV")
    transactions_file = st.file_uploader("Upload Monarch Transactions CSV", type="csv", key="txn")

    if transactions_file:
        df_txn = pd.read_csv(transactions_file)
        df_txn.columns = [col.strip() for col in df_txn.columns]

        if 'Date' in df_txn.columns:
            df_txn['Date'] = pd.to_datetime(df_txn['Date'])

        st.success(f"{len(df_txn)} transactions loaded!")

        income = df_txn[df_txn['Amount'] > 0]['Amount'].sum()
        expenses = df_txn[df_txn['Amount'] < 0]['Amount'].sum()
        cash_flow = income + expenses

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"${income:,.2f}")
        col2.metric("Total Expenses", f"${expenses:,.2f}")
        col3.metric("Net Cash Flow", f"${cash_flow:,.2f}")

        # Monthly Cash Flow
        if 'Date' in df_txn.columns:
            df_txn['Month'] = df_txn['Date'].dt.to_period('M')
            monthly_cf = df_txn.groupby('Month')['Amount'].sum().reset_index()
            monthly_cf['Month'] = monthly_cf['Month'].astype(str)

            st.subheader("📈 Monthly Cash Flow")
            st.line_chart(monthly_cf.set_index('Month')['Amount'])

        # Category Breakdown
        if 'Category' in df_txn.columns:
            st.subheader("🛍️ Spending by Category")
            category_totals = df_txn[df_txn['Amount'] < 0].groupby('Category')['Amount'].sum().sort_values()
            st.bar_chart(category_totals)

        # Recurring Expenses Detection
        st.subheader("🔁 Recurring Expenses")
        grouping_col = None
        for col_option in ['Description', 'Payee', 'Account Name']:
            if col_option in df_txn.columns:
                grouping_col = col_option
                break

        if grouping_col:
            recurring = df_txn.groupby([grouping_col, df_txn['Date'].dt.to_period('M')]).size().unstack().fillna(0)
            recurring['Recurring Count'] = (recurring > 0).sum(axis=1)
            recurring_expenses = recurring[recurring['Recurring Count'] >= 3].sort_values('Recurring Count', ascending=False)

            st.markdown(f"Using **{grouping_col}** to detect recurring expenses.")
            st.dataframe(recurring_expenses[['Recurring Count']])

            # Full Transaction Table
            st.subheader("📄 All Transactions")
            st.dataframe(df_txn.sort_values('Date', ascending=False))

        else:
            st.warning("⚠️ No suitable column found (like 'Description', 'Payee', or 'Account Name') to detect recurring expenses.")

    else:
        st.info("Upload a transactions CSV file to begin.")

# ---------------------- ACCOUNTS TAB ----------------------
with tab2:
    st.header("💰 Upload Accounts CSV")
    accounts_file = st.file_uploader("Upload Monarch Accounts CSV (Net Worth)", type="csv", key="acct")

    if accounts_file:
        df_accounts = pd.read_csv(accounts_file)
        df_accounts.columns = [col.strip() for col in df_accounts.columns]

        if 'Date' in df_accounts.columns:
            df_accounts['Date'] = pd.to_datetime(df_accounts['Date'])

        st.success("Accounts data loaded.")

        # Net Worth Over Time
        if all(col in df_accounts.columns for col in ['Account', 'Amount', 'Date']):
            net_worth = df_accounts.groupby('Date')['Amount'].sum().reset_index()
            st.subheader("📉 Net Worth Over Time")
            st.line_chart(net_worth.set_index('Date'))

            # Net Worth Change
            nw_change = net_worth['Amount'].iloc[-1] - net_worth['Amount'].iloc[0]
            st.metric("Change in Net Worth", f"${nw_change:,.2f}")
        else:
            st.warning("Missing required columns in accounts CSV: 'Account', 'Amount', or 'Date'.")

    else:
        st.info("Upload an accounts CSV to track assets & liabilities.")

# ---------------------- INSIGHTS TAB ----------------------
with tab3:
    st.header("📊 Insights (Coming Soon)")
    st.info("Future enhancements: savings rate, burn rate, category-level volatility, and financial health score.")

# ---------------------- PDF REPORT TAB ----------------------
with tab4:
    st.header("📄 PDF Report (Coming Soon)")
    st.info("Generate printable personal finance summaries for your records or clients.")
