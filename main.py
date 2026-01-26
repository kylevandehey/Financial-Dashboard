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
from src.nav import render_left_nav
from src.transactions.page import render_transactions_page

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
    render_transactions_page(transactions)

elif active_page == "insights":
    st.markdown("# 💡 Insights")
    st.info("Insights coming next.")

elif active_page == "loan_tracker":
    st.markdown("# 🏠 Loan Tracker")
    st.info("Loan Tracker coming soon.")

elif active_page == "tools":
    st.markdown("# 🛠 Tools")
    st.info("Tools coming soon.")

elif active_page == "assistance":
    st.markdown("# 💬 Assistance")
    st.info("Assistance coming soon.")
