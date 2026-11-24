import streamlit as st, pandas as pd, plotly.express as px
from analysis_engine.ui import *
from analysis_engine.phenotypes import derive_duration_normalised_phenotypes,CANDIDATE_PHENOTYPES
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Phenotype analysis','Construct and compare candidate methane signal phenotypes and duration-normalised measures.')
df=derive_duration_normalised_phenotypes(get_data());available=[c for c in CANDIDATE_PHENOTYPES if c in df]
if not available: st.info('No recognised candidate phenotype columns. Check source variable mapping and naming.');st.stop()
chosen=st.multiselect('Candidate phenotype measures',available,default=available)
if chosen:
    summary=df[chosen].apply(pd.to_numeric,errors='coerce').describe(percentiles=[.05,.25,.5,.75,.95]).T
    st.dataframe(summary,use_container_width=True)
    long=df[chosen].melt(var_name='phenotype',value_name='value').dropna()
    st.plotly_chart(px.box(long,x='phenotype',y='value',points='outliers',title='Candidate phenotype distributions'),use_container_width=True)
    st.download_button('Download phenotype summary',summary.to_csv(),'phenotype_summary.csv')
st.info('Candidate selection should combine construct validity, repeatability, duration sensitivity, biological relevance and predictive utility. Sensor-derived signals are not mass flux without calibration.')
