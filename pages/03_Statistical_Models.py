import streamlit as st
from analysis_engine.ui import *
from analysis_engine.statistics import fit_ols,fit_gee,fit_mixedlm
from analysis_engine.ui import render_sidebar_navigation
from analysis_engine.settings_config import load_active_settings
render_sidebar_navigation()
_cfg = load_active_settings(st.session_state)
_stats_cfg = _cfg.get("statistics", {})

header('Statistical models','Fit conventional models with explicit handling of repeated animal measurements.')
df=get_data();nums=numeric_cols(df);roles=get_roles(df)
outcome=choose_col(df,'Outcome variable',roles.get('methane'),nums)
predictors=st.multiselect('Fixed-effect predictors',[c for c in df.columns if c!=outcome],default=[c for c in [roles.get('breed'),roles.get('sex'),roles.get('round'),roles.get('weight')] if c and c!=outcome])
animal=choose_col(df,'Animal identifier',roles.get('animal_id'))
method=st.radio('Model specification',['OLS with HC3 robust SE','GEE exchangeable correlation','Linear mixed-effects random intercept'],horizontal=True)
alpha = st.number_input('Significance threshold (α)', min_value=0.001, max_value=0.20, value=float(_stats_cfg.get('alpha', 0.05)), step=0.005, format='%.3f')
if st.button('Fit statistical model',type='primary'):
    try:
        fit=fit_ols(df,outcome,predictors) if method.startswith('OLS') else fit_gee(df,outcome,predictors,animal) if method.startswith('GEE') else fit_mixedlm(df,outcome,predictors,animal)
        st.text(fit.summary().as_text());st.download_button('Download model summary',fit.summary().as_text(),'statistical_model_summary.txt')
        try:
            import pandas as pd
            ci = fit.conf_int()
            effects = pd.DataFrame({'estimate': fit.params, 'std_error': fit.bse, 'p_value': fit.pvalues, 'ci_lower': ci.iloc[:, 0], 'ci_upper': ci.iloc[:, 1]})
            effects['significant_at_alpha'] = effects['p_value'] < float(alpha)
            st.subheader('Coefficient interpretation')
            st.caption(f'An effect is flagged when p < {alpha:.3f}; this threshold does not replace multiple-testing correction or scientific interpretation.')
            st.dataframe(effects.reset_index(names='term'), use_container_width=True, hide_index=True)
            st.download_button('Download coefficient table', effects.reset_index(names='term').to_csv(index=False).encode(), 'statistical_model_coefficients.csv', 'text/csv')
        except Exception as table_error:
            st.warning(f'Coefficient table unavailable for this model result: {table_error}')
    except Exception as e: st.error(f'Model fitting failed: {e}')
st.caption('Use OLS only when independence assumptions are defensible. GEE and mixed-effects models account for within-animal dependence under different estimands and assumptions.')


st.divider()
st.page_link("pages/38_Conventional_vs_ML_Comparison.py", label="Compare conventional models with machine learning", icon="⚖️")
