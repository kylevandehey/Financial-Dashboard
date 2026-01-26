# main.py

import streamlit as st

from src.config import APP_TITLE
from src.theme import apply_theme_a

# --------------------------------------------------
# App Config (MUST be first Streamlit call)
# --------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded",  # user can still resize/collapse
)

# --------------------------------------------------
# Theme (AFTER page config)
# --------------------------------------------------
apply_theme_a()

# --------------------------------------------------
# Imports (after theme)
# --------------------------------------------------
from ui.control_panel import render_control_panel
from src.dashboard import render_dashboard_page
from ui.transactions import render_transactions_tab
from src.nav import render_left_nav

# -------------------------------------------------
# Sidebar: Navigation + Uploads
# -------------------------------------------------
active_page = render_left_nav()

st.sidebar.markdown("### 📤 Upload Monarch CSVs")
control_state = render_control_panel()

transactions = control_state.transactions
accounts = control_state.accounts

if transactions.empty:
    st.info("Upload Monarch CSV exports to begin.")
    st.stop()

# -------------------------------------------------
# Main Content Routing
# -------------------------------------------------
if active_page == "dashboard":
    render_dashboard_page(transactions=transactions)

elif active_page == "transactions":
    render_transactions_tab(
        transactions=transactions,
        accounts=accounts,
    )

else:
    # Placeholder pages (until implemented)
    page_titles = {
        "insights": "🧠 Insights",
        "loan_tracker": "🏠 Loan Tracker",
        "tools": "🛠️ Tools",
        "assistance": "💬 Assistance",
    }
    st.markdown(f"# {page_titles.get(active_page,'📄 Page')}")
    st.info("Temporarily disabled during dashboard rebuild.")
