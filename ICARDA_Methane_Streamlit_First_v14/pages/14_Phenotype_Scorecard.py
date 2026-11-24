import streamlit as st, pandas as pd
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Integrated phenotype scorecard','Review evidence across measurement quality, reliability, validity and predictive utility.')
df=get_data();r=get_roles(df);nums=numeric_cols(df)
items=['Data completeness and measurement QC','Construct validity and convergent evidence','Within-animal repeatability / reliability','Duration robustness','Biological relevance and allometric adjustment','Predictive utility under grouped validation','External validation / transportability']
rows=[]
for item in items:
    status=st.selectbox(item,['Not assessed','Preliminary','Evidence supportive','Evidence mixed','Evidence not supportive'],key='score_'+item)
    rows.append({'evidence_domain':item,'status':status})
tab=pd.DataFrame(rows);st.dataframe(tab,use_container_width=True)
if st.button('Export scorecard'):
    st.download_button('Download scorecard CSV',tab.to_csv(index=False),'phenotype_evidence_scorecard.csv')
st.info('This is an evidence register, not an automatic weighted score. Agree evidence thresholds and weights with the scientific team before ranking candidate phenotypes.')
