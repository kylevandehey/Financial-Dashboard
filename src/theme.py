import streamlit as st

def apply_theme_a() -> None:
    """
    Theme A: Copilot-like dark UI polish.
    Safe: CSS only. No data/calculation changes.
    """
    st.markdown(
        """
<style>
/* ---- App canvas ---- */
html, body, [class*="stApp"] {
  background: #0B0F14;
}

/* ---- Remove some default padding harshness ---- */
.block-container {
  padding-top: 1.4rem;
  padding-bottom: 2rem;
}

/* ---- Cards / sections ---- */
.af-card {
  background: linear-gradient(180deg, rgba(18,24,38,0.92), rgba(18,24,38,0.78));
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.22);
}

/* ---- Soft section separators ---- */
.af-divider {
  height: 1px;
  background: rgba(255,255,255,0.06);
  margin: 14px 0 18px 0;
}

/* ---- Headings ---- */
h1, h2, h3 {
  letter-spacing: 0.2px;
}
.af-subtle {
  color: rgba(230,234,242,0.75);
}

/* ---- Metric polish ---- */
[data-testid="stMetric"] {
  background: rgba(18,24,38,0.60);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 12px 12px 10px 12px;
}

/* ---- Pills (multiselect chips) ---- */
[data-baseweb="tag"] {
  background-color: rgba(255, 77, 77, 0.16) !important;
  border: 1px solid rgba(255, 77, 77, 0.35) !important;
}
[data-baseweb="tag"] span {
  color: #FFB3B3 !important;
}

/* ---- Expanders ---- */
details {
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  background: rgba(18,24,38,0.40);
  padding: 8px 10px;
}

/* ---- Tooltips (custom span) ---- */
.af-tip {
  display: inline-block;
  margin-left: 6px;
  color: rgba(230,234,242,0.55);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px;
  padding: 0px 7px;
  font-size: 12px;
  line-height: 18px;
}
.af-tip:hover {
  color: rgba(230,234,242,0.90);
  border-color: rgba(77,163,255,0.55);
}
</style>
        """,
        unsafe_allow_html=True,
    )
