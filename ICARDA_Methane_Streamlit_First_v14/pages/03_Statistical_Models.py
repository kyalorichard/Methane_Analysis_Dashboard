import streamlit as st
from analysis_engine.ui import *
from analysis_engine.statistics import fit_ols,fit_gee,fit_mixedlm
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Statistical models','Fit conventional models with explicit handling of repeated animal measurements.')
df=get_data();nums=numeric_cols(df);roles=get_roles(df)
outcome=choose_col(df,'Outcome variable',roles.get('methane'),nums)
predictors=st.multiselect('Fixed-effect predictors',[c for c in df.columns if c!=outcome],default=[c for c in [roles.get('breed'),roles.get('sex'),roles.get('round'),roles.get('weight')] if c and c!=outcome])
animal=choose_col(df,'Animal identifier',roles.get('animal_id'))
method=st.radio('Model specification',['OLS with HC3 robust SE','GEE exchangeable correlation','Linear mixed-effects random intercept'],horizontal=True)
if st.button('Fit statistical model',type='primary'):
    try:
        fit=fit_ols(df,outcome,predictors) if method.startswith('OLS') else fit_gee(df,outcome,predictors,animal) if method.startswith('GEE') else fit_mixedlm(df,outcome,predictors,animal)
        st.text(fit.summary().as_text());st.download_button('Download model summary',fit.summary().as_text(),'statistical_model_summary.txt')
    except Exception as e: st.error(f'Model fitting failed: {e}')
st.caption('Use OLS only when independence assumptions are defensible. GEE and mixed-effects models account for within-animal dependence under different estimands and assumptions.')
