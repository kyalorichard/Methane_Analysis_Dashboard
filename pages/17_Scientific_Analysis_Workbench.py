import streamlit as st
from analysis_engine.ui import header, render_sidebar_navigation

render_sidebar_navigation()
header("Scientific Analysis Workbench — focused workflows",
       "The former all-in-one workbench has been separated into focused analytical destinations with explicit methods and assumptions.")
st.info("Choose the dedicated workflow for the method you need. This avoids maintaining parallel implementations of reliability, inference, robustness and clustering.")
links = [
    ("Reliability, repeatability and agreement", "pages/33_Reliability_and_Agreement.py", "📏"),
    ("Group comparisons", "pages/08_Group_Comparisons.py", "⚖️"),
    ("Allometry, quantile regression and advanced inference", "pages/31_Advanced_Inference.py", "📈"),
    ("Sensitivity and robustness", "pages/12_Sensitivity_Robustness.py", "🛡️"),
    ("PCA and clustering", "pages/05_Clustering_PCA.py", "🧩"),
    ("Scientific reporting and reproducibility", "pages/27_Scientific_Publication_Suite.py", "📚"),
]
for label, target, icon in links:
    st.page_link(target, label=label, icon=icon, use_container_width=True)
