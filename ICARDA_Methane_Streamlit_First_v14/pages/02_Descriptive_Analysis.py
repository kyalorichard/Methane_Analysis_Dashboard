import streamlit as st, pandas as pd, plotly.express as px
from analysis_engine.ui import *
from analysis_engine.metrics import descriptive_table
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Descriptive analysis','Explore distributions, summary statistics and phenotype relationships.')
df=get_data();nums=numeric_cols(df)
if not nums: st.info('No numeric variables found.');st.stop()
sel=st.multiselect('Variables for summary',nums,default=nums[:min(8,len(nums))])
if sel:
    tab=descriptive_table(df,sel);st.dataframe(tab,use_container_width=True)
    st.download_button('Download descriptive statistics',tab.to_csv(index=False),'descriptive_statistics.csv')
    c1,c2=st.columns(2)
    with c1: distribution(df,st.selectbox('Distribution variable',sel,key='dist_var'))
    with c2:
        if len(sel)>1: st.plotly_chart(correlation_plot(df[sel]) if False else px.imshow(df[sel].corr(),text_auto='.2f',color_continuous_scale='RdBu_r',zmin=-1,zmax=1,title='Pearson correlation'),use_container_width=True)
if get_roles(df).get('breed') and len(nums):
    st.subheader('Stratified summaries');grp=st.selectbox('Grouping variable',[c for c in df.columns if df[c].nunique()<30],index=0);out=st.selectbox('Outcome',nums);st.dataframe(grouped_summary(df,grp,out),use_container_width=True)
