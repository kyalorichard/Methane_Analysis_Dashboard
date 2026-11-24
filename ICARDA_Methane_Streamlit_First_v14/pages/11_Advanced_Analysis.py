import streamlit as st, pandas as pd, numpy as np, plotly.express as px
import statsmodels.formula.api as smf
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Advanced scientific analysis','Explore allometric scaling, nonlinear relationships and distribution-sensitive associations.')
df=get_data();nums=numeric_cols(df);r=get_roles(df)
y=choose_col(df,'Phenotype outcome',r.get('methane'),nums);x=choose_col(df,'Body-size / predictor variable',r.get('weight'),[c for c in nums if c!=y])
d=df[[x,y]].copy();d[x]=pd.to_numeric(d[x],errors='coerce');d[y]=pd.to_numeric(d[y],errors='coerce');d=d.dropna()
st.plotly_chart(px.scatter(d,x=x,y=y,trendline='lowess',title=f'{y} versus {x}'),use_container_width=True)
if st.checkbox('Fit log–log allometric regression'):
    pos=d[(d[x]>0)&(d[y]>0)].copy()
    if len(pos)>=10:
        fit=smf.ols(f'np.log(Q("{y}")) ~ np.log(Q("{x}"))',data=pos).fit(cov_type='HC3');st.text(fit.summary().as_text());st.metric('Allometric exponent',f'{fit.params.iloc[1]:.3f}')
    else: st.warning('At least 10 positive paired observations are required for log–log regression.')
st.caption('The log–log slope is an estimated scaling exponent for the selected signal and covariate. Check residuals, influential points and biological interpretation before reporting.')
