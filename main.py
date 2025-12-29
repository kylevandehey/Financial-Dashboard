# Monarch+ Financial Dashboard — Full Skeleton with Advanced Planning Features

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from io import StringIO
import base64

# ---------- Setup ----------

st.set_page_config(page_title="Monarch+ Dashboard", layout="wide")
st.markdown("""<style>section.main {padding-top: 1rem;} .element-container {padding-bottom: 0.75rem;} </style>""", unsafe_allow_html=True)

# ---------- Session State ----------

if "uploaded_files" not in st.session_state:
st.session_state.uploaded_files = {}

# ---------- Sidebar (revised) ----------

with st.sidebar:
st.header("👤 User Settings")
user_name = st.text_input("User Name", value="Guest")

```
st.markdown("---")
st.subheader("🕓 Upload History")
if st.session_state.uploaded_files:
    for k, v in st.session_state.uploaded_files.items():
        st.markdown(f"**{k}** — {v['timestamp']}")
else:
    st.caption("No uploads yet.")
```

# ---------- File Loaders ----------

@st.cache_data(show_spinner=False)
def load_csv(uploaded_file):
return pd.read_csv(uploaded_file, parse_dates=True)

def get_date_bounds(df):
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
return df["Date"].min(), df["Date"].max()

def format_currency(val):
return f"(${abs(val):,.2f})" if val < 0 else f"${val:,.2f}"

# ---------- Tab Controls ----------

tabs = st.tabs(["📊 Dashboard", "🧾 Transactions", "📈 Insights", "📄 PDF Report", "🧮 Loan Tracker", "💬 Assistant", "🧠 Tools"])

# ---------- TAB 1: Dashboard ----------

with tabs[0]:
st.title("📊 Monarch+ Personal Finance Dashboard")
st.subheader("📁 Upload Transactions CSV")

```
uploaded_files = st.file_uploader("Upload Monarch CSV Files", accept_multiple_files=True, type="csv")
file_registry = {}

for file in uploaded_files:
    df = load_csv(file)
    st.session_state.uploaded_files[file.name] = {
        "df": df,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    file_registry[file.name] = df

if "transactions" in file_registry:
    df_txn = file_registry["transactions"]
    df_txn["Date"] = pd.to_datetime(df_txn["Date"], errors="coerce")

    first_date, last_date = get_date_bounds(df_txn)
    total_txns = len(df_txn)
    income = df_txn[df_txn["Amount"] > 0]["Amount"].sum()
    expenses = df_txn[df_txn["Amount"] < 0]["Amount"].sum()
    net = income + expenses

    st.markdown("---")
    st.subheader("📈 High-Level Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Transactions", f"{total_txns:,}")
    col2.metric("First Transaction", first_date.date())
    col3.metric("Last Transaction", last_date.date())
    col4.metric("Net Cash Flow", format_currency(net))

    col5, col6, col7 = st.columns(3)
    col5.metric("Total Income", format_currency(income))
    col6.metric("Total Expenses", format_currency(expenses))

# Placeholder for accounts CSV
if "accounts" in file_registry:
    df_acct = file_registry["accounts"]
    try:
        total_assets = df_acct[df_acct["Type"] == "Asset"]["Balance"].sum()
        total_liabilities = df_acct[df_acct["Type"] == "Liability"]["Balance"].sum()
        net_equity = total_assets - total_liabilities

        st.markdown("---")
        st.subheader("🏦 Accounts Overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("Assets", format_currency(total_assets))
        col2.metric("Liabilities", format_currency(total_liabilities))
        col3.metric("Net Equity", format_currency(net_equity))
    except:
        st.warning("Accounts CSV found but does not have expected structure.")

st.markdown("---")
st.caption("Note: Monarch Money allows CSV exports for: Transactions, Accounts, and Categories.")
```

# ---------- TAB 2: Transactions ----------

with tabs[1]:
st.header("🧾 Transactions")
if "transactions" in file_registry:
df_txn = file_registry["transactions"]

```
    st.subheader("📅 Date Range Filters")
    preset = st.selectbox("Date Range Presets", ["Year to Date", "Last 30 Days", "Last 90 Days", "Last 12 Months", "All Time"])

    today = datetime.date.today()
    if preset == "Year to Date":
        start = datetime.date(today.year, 1, 1)
    elif preset == "Last 30 Days":
        start = today - datetime.timedelta(days=30)
    elif preset == "Last 90 Days":
        start = today - datetime.timedelta(days=90)
    elif preset == "Last 12 Months":
        start = today - datetime.timedelta(days=365)
    else:
        start = df_txn["Date"].min().date()
    end = today

    df_filtered = df_txn[(df_txn["Date"] >= pd.to_datetime(start)) & (df_txn["Date"] <= pd.to_datetime(end))]

    st.caption(f"Showing transactions from {start} to {end}.")

    income = df_filtered[df_filtered["Amount"] > 0]["Amount"].sum()
    expenses = df_filtered[df_filtered["Amount"] < 0]["Amount"].sum()
    net = income + expenses

    col1, col2, col3 = st.columns(3)
    col1.metric("Income", format_currency(income))
    col2.metric("Expenses", format_currency(expenses))
    col3.metric("Net", format_currency(net))

    st.subheader("📈 Monthly Cash Flow")
    df_filtered["Month"] = df_filtered["Date"].dt.to_period("M")
    df_plot = df_filtered.groupby("Month")["Amount"].sum().reset_index()
    df_plot["Month"] = df_plot["Month"].astype(str)
    fig = px.line(df_plot, x="Month", y="Amount", title="Cash Flow by Month")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📊 Full Transaction Table")
    st.dataframe(df_filtered, use_container_width=True)
else:
    st.info("Please upload a transactions CSV on the Dashboard tab.")
```

# ---------- TAB 3: Insights (Placeholder) ----------

with tabs[2]:
st.header("📈 Insights")
st.write("Advanced visualizations, category-level volatility, rolling averages, savings rate, and burn rate coming soon.")

# ---------- TAB 4: PDF Report (Placeholder) ----------

with tabs[3]:
st.header("📄 PDF Report Generator")
st.write("Export your data as a client-friendly PDF. Will include key metrics, graphs, and optional notes.")

# ---------- TAB 5: Loan Tracker ----------

with tabs[4]:
st.header("🧮 Loan Tracker & Leverage Analysis")
st.info("Track your loans and compare payoff vs invest scenarios.")

# ---------- TAB 6: Assistant ----------

with tabs[5]:
st.header("💬 Chat Assistant")
st.write("Ask questions about your financial data or get help using this dashboard.")
user_q = st.text_input("Ask something:")
if user_q:
st.info("(Chatbot integration coming soon — this will use OpenAI API or Langchain)")

# ---------- TAB 7: Tools ----------

with tabs[6]:
st.header("🧠 Tools & Calculators")
st.subheader("Loan Calculator")
with st.expander("🧮 Simple Loan Calculator"):
loan_amt = st.number_input("Loan Amount", value=10000)
rate = st.number_input("Interest Rate (%)", value=6.0)
years = st.number_input("Term (years)", value=5)
if st.button("Calculate Loan"):
r = rate / 100 / 12
n = years * 12
pmt = loan_amt * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
st.success(f"Monthly Payment: {format_currency(pmt)}")

```
st.markdown("---")
st.caption("Future features: Retirement simulator, tax readiness score, savings goal planner, etc.")
```




