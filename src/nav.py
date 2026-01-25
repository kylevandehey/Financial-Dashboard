# src/nav.py

import streamlit as st
from src.pages import PAGES

_NAV_KEY = "active_page"
_SIDEBAR_MODE_KEY = "sidebar_mode"  # "expanded" | "collapsed"

def _init_nav_state() -> None:
    if _NAV_KEY not in st.session_state:
        st.session_state[_NAV_KEY] = "dashboard"
    if _SIDEBAR_MODE_KEY not in st.session_state:
        st.session_state[_SIDEBAR_MODE_KEY] = "expanded"

def render_left_nav() -> str:
    """
    Returns the selected page key.
    Sidebar is resizable by default; user can also collapse via toggle.
    """
    _init_nav_state()

    st.sidebar.markdown("### 🧭 Navigation")

    # Optional user-controlled collapse (Streamlit sidebar is inherently resizable)
    compact = st.sidebar.toggle("Compact sidebar", value=(st.session_state[_SIDEBAR_MODE_KEY] == "collapsed"))
    st.session_state[_SIDEBAR_MODE_KEY] = "collapsed" if compact else "expanded"

    # Pill-like navigation using buttons. We use a single-column layout for stability.
    for p in PAGES:
        is_active = (st.session_state[_NAV_KEY] == p.key)
        label = f"{p.icon} {p.label}" if not compact else f"{p.icon}"

        # Use different button types to simulate active state.
        btn_type = "primary" if is_active else "secondary"

        if st.sidebar.button(label, key=f"nav_{p.key}", use_container_width=True, type=btn_type):
            st.session_state[_NAV_KEY] = p.key
            st.rerun()

    st.sidebar.divider()
    return st.session_state[_NAV_KEY]
