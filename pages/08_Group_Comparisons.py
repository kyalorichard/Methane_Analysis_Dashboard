import streamlit as st, pandas as pd, numpy as np, plotly.express as px
from scipy import stats
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
from analysis_engine.settings_config import load_active_settings
render_sidebar_navigation()
_cfg = load_active_settings(st.session_state)
_alpha = float(_cfg.get("statistics", {}).get("alpha", 0.05))

header('Group comparisons','Compare phenotype distributions across breed, sex, round or management groups.')
df=get_data();nums=numeric_cols(df);groups=[c for c in df.columns if 2<=df[c].nunique(dropna=True)<=20]
group=choose_col(df,'Grouping variable',get_roles(df).get('breed'),groups);out=choose_col(df,'Phenotype outcome',get_roles(df).get('methane'),nums)
s=grouped_summary(df,group,out);st.dataframe(s,use_container_width=True)
d=df[[group,out]+([get_roles(df).get('animal_id')] if get_roles(df).get('animal_id') else [])].copy();d[out]=pd.to_numeric(d[out],errors='coerce');d=d.dropna()
st.plotly_chart(px.box(d,x=group,y=out,color=group,points='outliers',title=f'{out} by {group}'),use_container_width=True)
vals=[g[out].values for _,g in d.groupby(group) if len(g)>1]
if len(vals)==2:
    test=stats.mannwhitneyu(vals[0],vals[1],alternative='two-sided')
    st.metric('Unadjusted Mann–Whitney p-value',f'{test.pvalue:.4g}')
    st.caption(f'Configured significance threshold: α = {_alpha:.3f}. This is an unadjusted exploratory test.')
    st.caption('Unadjusted record-level comparison only. With repeated observations, use an animal-level or mixed-model comparison for inference.')
elif len(vals)>2:
    test=stats.kruskal(*vals);st.metric('Unadjusted Kruskal–Wallis p-value',f'{test.pvalue:.4g}')
    st.caption(f'Configured significance threshold: α = {_alpha:.3f}. This is an unadjusted exploratory test.')
st.warning('These descriptive tests do not adjust for repeated records, confounding or multiple comparisons. Do not interpret group differences as causal effects.')
