import streamlit as st
from analysis_engine.ui import header, render_sidebar_navigation

render_sidebar_navigation()
header("Advanced nonlinear analysis consolidated",
       "Allometric scaling and nonlinear inference are maintained in the focused Advanced Inference workspace.")
st.info("This compatibility route remains available for older bookmarks. Use the canonical inference workspace for current analyses.")
st.page_link("pages/31_Advanced_Inference.py", label="Open Advanced Inference & Scaling", icon="📈")
