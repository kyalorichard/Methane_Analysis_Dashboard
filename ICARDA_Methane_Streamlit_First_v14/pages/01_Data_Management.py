import streamlit as st, pandas as pd
from analysis_engine.ui import *
from analysis_engine.io import infer_roles, validate_dataset
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Data management & quality control','Inspect source records, map biological variables and document dataset integrity.')
df=get_data(); roles=get_roles(df)
metric_row([('RECORDS',f'{len(df):,}','Source rows'),('VARIABLES',str(df.shape[1]),'Source columns'),('DUPLICATES',f'{df.duplicated().sum():,}','Exact duplicate rows'),('MISSING CELLS',f'{df.isna().sum().sum():,}','Missing values')])
st.subheader('Variable mapping')
role_names=['animal_id','species','breed','sex','weight','round','date','recording_duration','member','methane']
cols=st.columns(2)
for i,role in enumerate(role_names):
    opts=['—']+list(df.columns);cur=roles.get(role);ix=opts.index(cur) if cur in opts else 0
    roles[role]=cols[i%2].selectbox(role.replace('_',' ').title(),opts,index=ix,key='map_'+role)
st.session_state['roles']=roles
st.subheader('Data preview');st.dataframe(df.head(100),use_container_width=True,height=300)
st.subheader('Missingness profile');m=(df.isna().mean()*100).sort_values(ascending=False).rename('missing_percent').reset_index(names='variable');st.dataframe(m,use_container_width=True)
st.subheader('QC checklist')
for issue in validate_dataset(df): st.warning(issue)
if not validate_dataset(df): st.success('Basic structural checks passed. Confirm domain-specific ranges and instrument quality before formal analysis.')
st.download_button('Download data dictionary',pd.DataFrame({'variable':df.columns,'dtype':[str(x) for x in df.dtypes],'missing_n':df.isna().sum().values,'missing_percent':(df.isna().mean()*100).round(2).values}).to_csv(index=False),'data_dictionary.csv')
