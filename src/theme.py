# src/theme.py
import streamlit as st

def apply_theme_a():
    st.markdown(
        """
        <style>
        /* Copilot-style dark theme */
        html, body, [class*="css"] {
            background-color: #0E1117;
            color: #FAFAFA;
        }

        .stMetric {
            background: linear-gradient(180deg, #111827, #0B1220);
            border-radius: 12px;
            padding: 12px;
        }

        /* Buttons */
        .stButton>button {
            background-color: #1F2937;
            color: #E5E7EB;
            border-radius: 8px;
            border: 1px solid #374151;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
