import streamlit as st, pandas as pd, plotly.express as px
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
from analysis_engine.longitudinal import paired_round_changes
render_sidebar_navigation()

header('Longitudinal analysis','Describe temporal and repeated-round patterns while retaining animal-level structure.')
df=get_data();r=get_roles(df);animal=r.get('animal_id');roundc=r.get('round');datec=r.get('date');nums=numeric_cols(df)
out=choose_col(df,'Phenotype outcome',r.get('methane'),nums)
if roundc:
    sm=grouped_summary(df,roundc,out);st.subheader('Phenotype by monitoring round');st.dataframe(sm,use_container_width=True)
    st.plotly_chart(px.box(df,x=roundc,y=out,points='outliers',title=f'{out} by round'),use_container_width=True)
if animal and roundc:
    d=df[[animal,roundc,out]].copy();d[out]=pd.to_numeric(d[out],errors='coerce');p=d.pivot_table(index=animal,columns=roundc,values=out,aggfunc='median')
    if p.shape[1]>=2:
        st.subheader('Paired animal-level changes')
        cols=list(p.columns)
        a,b=st.columns(2)
        a.selectbox('Baseline round',cols,key='base_round')
        base=st.session_state['base_round']
        comparison_options=[value for value in cols if value != base]
        # Streamlit preserves widget state across reruns. Reset a stale comparison
        # selection when it now equals the baseline or is no longer available.
        if st.session_state.get('comp_round') not in comparison_options:
            st.session_state['comp_round']=comparison_options[0]
        b.selectbox('Comparison round',comparison_options,key='comp_round')
        comp=st.session_state['comp_round']
        try:
            paired=paired_round_changes(p,base,comp)
        except ValueError as exc:
            st.warning(str(exc))
        else:
            if paired.empty:
                st.info('No animals have non-missing measurements in both selected rounds.')
            else:
                metric_row([('PAIRED ANIMALS',f'{len(paired):,}','Complete pair'),('MEDIAN CHANGE',f'{paired.change.median():.3f}','Comparison minus baseline'),('MEAN CHANGE',f'{paired.change.mean():.3f}','Comparison minus baseline')])
                st.plotly_chart(px.histogram(paired,x='change',nbins=30,title='Distribution of within-animal change'),use_container_width=True)
if datec:
    t=df[[datec,out]].copy();t[datec]=pd.to_datetime(t[datec],errors='coerce');t[out]=pd.to_numeric(t[out],errors='coerce');t=t.dropna().set_index(datec).sort_index()
    if len(t): st.plotly_chart(px.line(t.resample('ME')[out].mean().reset_index(),x=datec,y=out,title='Monthly aggregate mean (descriptive)'),use_container_width=True)
st.warning('Aggregate time trends are descriptive. Forecasting requires adequate temporal density, regularity and out-of-time validation.')
