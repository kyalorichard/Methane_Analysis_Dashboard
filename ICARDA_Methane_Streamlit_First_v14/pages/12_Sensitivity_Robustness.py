import streamlit as st, pandas as pd, numpy as np, plotly.express as px
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Sensitivity & robustness','Evaluate how phenotype summaries change under alternative recording-duration restrictions.')
df=get_data();r=get_roles(df);dur=r.get('recording_duration');nums=numeric_cols(df);out=choose_col(df,'Phenotype outcome',r.get('methane'),nums)
if not dur: st.error('Map recording duration in Data Management.');st.stop()
d=df[[dur,out]].copy();d[dur]=pd.to_numeric(d[dur],errors='coerce');d[out]=pd.to_numeric(d[out],errors='coerce');d=d.dropna()
metric_row([('RECORDS',f'{len(d):,}','Valid duration/outcome pairs'),('MEDIAN DURATION',f'{d[dur].median():.1f}s','Observed median'),('DURATION RANGE',f'{d[dur].min():.1f}–{d[dur].max():.1f}s','Observed range')])
threshold=st.slider('Minimum recording duration (seconds)',int(max(0,d[dur].min())),int(d[dur].max()),int(d[dur].quantile(.25)))
sub=d[d[dur]>=threshold]
metric_row([('RETAINED RECORDS',f'{len(sub):,}',f'{len(sub)/len(d)*100:.1f}% of valid pairs'),('MEAN OUTCOME — ALL',f'{d[out].mean():.3f}','All valid records'),('MEAN OUTCOME — FILTERED',f'{sub[out].mean():.3f}' if len(sub) else 'N/A','Duration restricted')])
comp=pd.DataFrame({'analysis':['All records',f'Duration ≥ {threshold}s'],'n':[len(d),len(sub)],'mean':[d[out].mean(),sub[out].mean() if len(sub) else np.nan],'median':[d[out].median(),sub[out].median() if len(sub) else np.nan]});st.dataframe(comp,use_container_width=True)
st.plotly_chart(px.scatter(d,x=dur,y=out,opacity=.45,trendline='lowess',title='Outcome versus recording duration'),use_container_width=True)
st.warning('Duration restriction is one sensitivity analysis, not proof of measurement validity. Compare effect magnitude and uncertainty across prespecified alternatives.')
