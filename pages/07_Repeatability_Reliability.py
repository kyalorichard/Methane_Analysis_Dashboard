import streamlit as st, pandas as pd, numpy as np, plotly.express as px
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Repeatability & reliability','Quantify within-animal consistency across repeated rounds or measurement sessions.')
df=get_data();r=get_roles(df);animal=r.get('animal_id');roundc=r.get('round');nums=numeric_cols(df)
if not animal or not roundc: st.error('Map both Animal ID and Round in Data Management.');st.stop()
out=choose_col(df,'Phenotype outcome',r.get('methane'),nums)
d=df[[animal,roundc,out]].copy();d[out]=pd.to_numeric(d[out],errors='coerce');d=d.dropna()
p=d.pivot_table(index=animal,columns=roundc,values=out,aggfunc='median')
metric_row([('ANIMALS WITH REPEATS',f'{int((p.notna().sum(axis=1)>=2).sum()):,}','At least two observed rounds'),('ROUNDS',str(p.shape[1]),'Observed round categories'),('PAIRED ANIMALS',f'{int(p.dropna().shape[0]):,}','Complete across all displayed rounds')])
if p.shape[1]>=2:
    st.plotly_chart(px.line(p.dropna().head(150).reset_index().melt(id_vars=animal),x='variable',y='value',color=animal,title='Within-animal trajectories (first 150 complete animals)',opacity=.18),use_container_width=True)
    # One-way random effects ICC(1,1) on balanced complete cases, explicitly labelled exploratory.
    q=p.dropna();k=q.shape[1];n=q.shape[0]
    if n>=3 and k>=2:
        grand=q.values.mean(); rowm=q.mean(axis=1).values; colm=q.mean(axis=0).values
        msb=k*np.sum((rowm-grand)**2)/(n-1); msw=np.sum((q.values-rowm[:,None])**2)/(n*(k-1))
        icc=(msb-msw)/(msb+(k-1)*msw) if (msb+(k-1)*msw)!=0 else np.nan
        st.metric('Exploratory ICC(1,1)',f'{icc:.3f}' if np.isfinite(icc) else 'Not estimable')
        st.caption(f'Balanced complete-case one-way random-effects ICC; n={n} animals, k={k} rounds. For formal reporting, select an ICC model matching the measurement design and obtain confidence intervals.')
    else: st.info('Insufficient balanced repeated observations for an ICC estimate.')
else: st.info('At least two rounds are required.')
st.warning('Repeatability is not heritability. This descriptive ICC does not account for all possible session, assessor or environmental effects.')
