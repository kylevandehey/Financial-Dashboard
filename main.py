import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
import base64

st.set_page_config(page_title="📊 Monarch+ Dashboard", layout="wide")
st.title("📊 Monarch+ Personal Finance Dashboard")

tab1, tab2, tab3, tab4 = st.tabs(["💸 Transactions", "💰 Accounts", "📊 Insights", "📄 PDF Report"])

# ------------- TRANSACTIONS TAB -------------
with tab1:
    st.header("💸 Upload Transactions CSV")
    transactions_file = st.file_uploader("Upload your Monarch Transactions CSV", type="csv", key="txn")

    if transactions_file:
        df_txn = pd.read_csv(transactions_file)
        df_txn['Date'] = pd.to_datetime(df_txn['Date'])
        df_txn.columns = [col.strip() for col in df_txn.columns]

        st.success(f"{len(df_txn)} transactions loaded!")
        
        # Metrics
        income = df_txn[df_txn['Amount'] > 0]['Amount'].sum()
        expenses = df_txn[df_txn['Amount'] < 0]['Amount'].sum()
        cash_flow = income + expenses

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"${income:,.2f}")
        col2.metric("Total Expenses", f"${expenses:,.2f}")
        col3.metric("Net Cash Flow", f"${cash_flow:,.2f}")

        # Monthly Cash Flow
        df_txn['Month'] = df_txn['Date'].dt.to_period('M')
        monthly_cf = df_txn.groupby('Month')['Amount'].sum().reset_index()
        monthly_cf['Month'] = monthly_cf['Month'].astype(str)

        st.subheader("📈 Monthly Cash Flow")
        st.line_chart(monthly_cf.set_index('Month')['Amount'])

        # Rolling 3-month average
        df_txn.set_index('Date', inplace=True)
        rolling_cf = df_txn.resample('M')['Amount'].sum().rolling(3).mean()
        st.subheader("📊 Rolling 3-Month Cash Flow Average")
        st.line_chart(rolling_cf)

        df_txn.reset_index(inplace=True)

        # Category Breakdown
        if 'Category' in df_txn.columns:
            st.subheader("🛍️ Spending by Category")
            category_totals = df_txn[df_txn['Amount'] < 0].groupby('Category')['Amount'].sum().sort_values()
            st.bar_chart(category_totals)

            # Volatility per Category
            st.subheader("⚖️ Volatility by Category")
            cat_vol = df_txn[df_txn['Amount'] < 0].groupby('Category')['Amount'].std().dropna()
            st.bar_chart(cat_vol)

       # Recurring Expense Detection
st.subheader("♻️ Detected Recurring Expenses")

# Try to find a good column for grouping recurring transactions
grouping_col = None
for col_option in ['Description', 'Payee', 'Merchant', 'Account Name']:
    if col_option in df_txn.columns:
        grouping_col = col_option
        break

if grouping_col:
    recurring = df_txn.groupby([grouping_col, df_txn['Date'].dt.to_period('M')]).size().unstack().fillna(0)
    recurring['Recurring Count'] = (recurring > 0).sum(axis=1)
    recurring_expenses = recurring[recurring['Recurring Count'] >= 3].sort_values('Recurring Count', ascending=False)

    st.markdown(f"Using **{grouping_col}** to detect recurring expenses.")
    st.dataframe(recurring_expenses[['Recurring Count']])
else:
    st.warning("No suitable column found (like 'Description', 'Payee', or 'Account Name') to detect recurring expenses.")

        # Full Transaction Table
        st.subheader("📃 All Transactions")
        st.dataframe(df_txn.sort_values('Date', ascending=False))

# ------------- ACCOUNTS TAB -------------
with tab2:
    st.header("💰 Upload Accounts CSV")
    accounts_file = st.file_uploader("Upload Monarch Accounts CSV (Net Worth)", type="csv", key="acct")

    if accounts_file:
        df_accounts = pd.read_csv(accounts_file)
        df_accounts['Date'] = pd.to_datetime(df_accounts['Date'])
        df_accounts.columns = [col.strip() for col in df_accounts.columns]

        st.success("Accounts data loaded.")
        
        # Group Net Worth Over Time
        if {'Account', 'Amount', 'Date'}.issubset(df_accounts.columns):
            net_worth = df_accounts.groupby('Date')['Amount'].sum().reset_index()
            st.subheader("📈 Net Worth Over Time")
            st.line_chart(net_worth.set_index('Date'))

            nw_change = net_worth['Amount'].iloc[-1] - net_worth['Amount'].iloc[0]
            st.metric("Change in Net Worth", f"${nw_change:,.2f}")
        else:
            st.error("Missing expected columns in Accounts CSV.")

# ------------- INSIGHTS TAB -------------
with tab3:
    st.header("📊 Advanced Metrics")
    if transactions_file:
        # Savings Rate
        total_income = df_txn[df_txn['Amount'] > 0]['Amount'].sum()
        total_expenses = -df_txn[df_txn['Amount'] < 0]['Amount'].sum()
        savings_rate = 100 * (total_income - total_expenses) / total_income if total_income else 0

        # Burn Rate = average monthly expenses
        monthly_burn = df_txn[df_txn['Amount'] < 0].groupby(df_txn['Date'].dt.to_period('M'))['Amount'].sum().mean()

        st.metric("💾 Savings Rate", f"{savings_rate:.2f}%")
        st.metric("🔥 Burn Rate (Monthly Avg)", f"${-monthly_burn:,.2f}")

        # Financial Health Score
        st.subheader("🧠 Financial Health Score (Experimental)")
        score = 0
        if savings_rate > 20: score += 40
        if -monthly_burn < total_income / 12: score += 30
        if recurring_expenses.shape[0] < 10: score += 30

        status = "⚠️ Needs Work" if score < 50 else "✅ Solid" if score < 80 else "🏆 Excellent"
        st.metric("Financial Health Score", f"{score}/100 - {status}")

# ------------- PDF REPORT TAB -------------
with tab4:
    st.header("📄 Generate PDF Report")
    st.markdown("This will export summary data to a downloadable PDF (experimental).")
    
    if transactions_file:
        report_content = f"""Monarch+ Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Transactions Loaded: {len(df_txn)}
Total Income: ${income:,.2f}
Total Expenses: ${expenses:,.2f}
Net Cash Flow: ${cash_flow:,.2f}
Savings Rate: {savings_rate:.2f}%
Burn Rate: ${-monthly_burn:,.2f}
Health Score: {score}/100 - {status}
        """

        def create_download_button(text, filename):
            b64 = base64.b64encode(text.encode()).decode()
            href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">📥 Download PDF Report</a>'
            return href

        st.markdown(create_download_button(report_content, "MonarchPlus_Report.txt"), unsafe_allow_html=True)
    else:
        st.info("Upload transactions first to enable report.")

