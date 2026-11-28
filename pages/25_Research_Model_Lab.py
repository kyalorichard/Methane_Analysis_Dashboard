import streamlit as st
from analysis_engine.ui import header, render_sidebar_navigation

render_sidebar_navigation()
header("Classification and mixed-effects workflows consolidated",
       "Animal-grouped classification is part of the Unified Research Model Lab; repeated-measures mixed-effects inference is part of Statistical Models.")
st.info("Use the canonical destinations below to avoid running parallel versions of the same workflow.")
st.page_link("pages/34_Advanced_ML_Explainability.py", label="Open classification and predictive validation", icon="🤖")
st.page_link("pages/03_Statistical_Models.py", label="Open mixed-effects and conventional statistical models", icon="📐")
