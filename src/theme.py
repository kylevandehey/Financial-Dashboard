# src/theme.py
import streamlit as st

def apply_theme_a():
    """
    Copilot-style dark theme with elevated cards, pill buttons,
    sidebar polish, and emoji-friendly typography.
    """
    st.markdown(
        """
        <style>

        /* -------------------------------------------------
           Base app + typography
        ------------------------------------------------- */
        html, body, [class*="css"] {
            background-color: #0B0F17;
            color: #E5E7EB;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                         Roboto, Helvetica, Arial, sans-serif;
        }

        h1, h2, h3, h4, h5 {
            color: #F9FAFB;
            letter-spacing: 0.2px;
        }

        /* Emoji alignment fix */
        h1 span, h2 span, h3 span {
            vertical-align: middle;
        }

        /* -------------------------------------------------
           Sidebar (Copilot-style left rail)
        ------------------------------------------------- */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0E1424, #0A0F1D);
            border-right: 1px solid #1F2937;
        }

        section[data-testid="stSidebar"] h3 {
            color: #9CA3AF;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.5rem;
        }

        /* -------------------------------------------------
           Buttons (pill-style nav + actions)
        ------------------------------------------------- */
        .stButton > button {
            background: linear-gradient(180deg, #1F2937, #111827);
            color: #E5E7EB;
            border-radius: 999px;
            border: 1px solid #374151;
            padding: 0.45rem 0.9rem;
            font-size: 0.9rem;
            transition: all 0.15s ease-in-out;
        }

        .stButton > button:hover {
            background: linear-gradient(180deg, #2563EB, #1D4ED8);
            color: #FFFFFF;
            border-color: #2563EB;
        }

        .stButton > button:active {
            transform: translateY(1px);
        }

        /* Primary button (active nav pill) */
        button[kind="primary"] {
            background: linear-gradient(180deg, #2563EB, #1D4ED8) !important;
            color: #FFFFFF !important;
            border: 1px solid #2563EB !important;
            font-weight: 600;
        }

        /* -------------------------------------------------
           Metric cards (financial health, snapshot, etc.)
        ------------------------------------------------- */
        .stMetric {
            background: linear-gradient(180deg, #0F172A, #0B1220);
            border-radius: 16px;
            padding: 14px 16px;
            border: 1px solid #1F2937;
            box-shadow:
                0 10px 25px rgba(0,0,0,0.35),
                inset 0 1px 0 rgba(255,255,255,0.03);
        }

        .stMetric label {
            color: #9CA3AF;
            font-size: 0.8rem;
        }

        .stMetric div[data-testid="stMetricValue"] {
            color: #F9FAFB;
            font-size: 1.4rem;
            font-weight: 600;
        }

        /* -------------------------------------------------
           Containers / sections
        ------------------------------------------------- */
        div[data-testid="stVerticalBlock"] > div {
            gap: 1.1rem;
        }

        .block-container {
            padding-top: 1.4rem;
            padding-left: 2.2rem;
            padding-right: 2.2rem;
        }

        /* -------------------------------------------------
           Expander (configure metrics, advanced controls)
        ------------------------------------------------- */
        details {
            background: linear-gradient(180deg, #0F172A, #0B1220);
            border-radius: 14px;
            border: 1px solid #1F2937;
            padding: 0.6rem 0.8rem;
        }

        summary {
            color: #E5E7EB;
            font-weight: 500;
            cursor: pointer;
        }

        /* -------------------------------------------------
           Charts (Plotly / Altair containers)
        ------------------------------------------------- */
        .js-plotly-plot,
        .vega-embed {
            background: #0B1220 !important;
            border-radius: 16px;
            padding: 0.5rem;
            border: 1px solid #1F2937;
        }

        /* -------------------------------------------------
           Data tables
        ------------------------------------------------- */
        .stDataFrame {
            background: #0B1220;
            border-radius: 14px;
            border: 1px solid #1F2937;
        }

        /* -------------------------------------------------
           Info / warning boxes
        ------------------------------------------------- */
        .stAlert {
            border-radius: 14px;
            border: 1px solid #1F2937;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
