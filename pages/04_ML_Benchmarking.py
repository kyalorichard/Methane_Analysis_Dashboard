import streamlit as st
from analysis_engine.ui import header, render_sidebar_navigation

render_sidebar_navigation()
header("Regression benchmarking moved to the Unified Research Model Lab",
       "The standard and nested animal-grouped regression workflows now live with learning curves, classification, prediction uncertainty, external validation and explainability.")
st.info("No functionality has been removed. Open the Unified Research Model Lab and select the Regression & phenotype prediction workflow.")
st.page_link("pages/34_Advanced_ML_Explainability.py", label="Open Unified Research Model Lab", icon="🤖")
st.page_link("pages/38_Conventional_vs_ML_Comparison.py", label="Compare conventional models with machine learning", icon="⚖️")
