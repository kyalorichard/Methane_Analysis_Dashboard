import streamlit as st, pandas as pd, json, zipfile, io, platform, datetime
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
from analysis_engine.service_registry import get_service
render_sidebar_navigation()

header('Reports & reproducibility exports','Export analysis-ready data, metadata and a reproducibility manifest.')
df=get_data();r=get_roles(df)
st.subheader('Export options')
a,b,c=st.columns(3)
a.download_button('Download active dataset (CSV)',df.to_csv(index=False),'analysis_dataset.csv','text/csv')
dictdf=pd.DataFrame({'variable':df.columns,'dtype':[str(x) for x in df.dtypes],'missing_n':df.isna().sum().values,'missing_percent':(df.isna().mean()*100).round(3).values})
b.download_button('Download data dictionary',dictdf.to_csv(index=False),'data_dictionary.csv','text/csv')
manifest={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'dataset_name':st.session_state.get('data_name'),'n_records':len(df),'n_variables':df.shape[1],'species':st.session_state.get('species'),'variable_roles':r,'python_version':platform.python_version(),'pandas_version':pd.__version__,'dataset_fingerprint_sha256':get_service('dataframe_fingerprint')(df),'random_seed_convention':42,'validation_note':'Repeated animal records should remain grouped in validation. Sensor signal proxies are not methane mass flux without calibration.'}
st.subheader('Run manifest');st.json(manifest)
st.download_button('Download run manifest (JSON)',json.dumps(manifest,indent=2),'run_manifest.json','application/json')
st.info('This export records the current session configuration. It does not yet package fitted model objects or all analysis figures into a complete archival bundle.')

st.page_link("pages/27_Scientific_Publication_Suite.py", label="Open the scientific publication suite", icon="📚")
