import json
import streamlit as st
import pandas as pd
from analysis_engine.research_methods import (dataset_validation_report, fit_random_slope_model,
    consensus_clustering, create_reproducibility_manifest)

st.set_page_config(page_title='Research Diagnostics & Methods', page_icon='🧬', layout='wide')
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()
st.title('Research Diagnostics & Methods')
st.caption('Advanced tools for dataset integrity, longitudinal modelling, phenotype clustering and reproducible research.')
if 'data' not in st.session_state:
    st.info('Load a dataset using the sidebar to access these workflows.')
    st.stop()
df=st.session_state['data']

st.header('1. Dataset integrity and quality checks')
report=dataset_validation_report(df)
c1,c2,c3,c4=st.columns(4)
c1.metric('Records',f"{report['n_records']:,}")
c2.metric('Variables',f"{report['n_variables']:,}")
c3.metric('Duplicate rows',f"{report['duplicate_rows']:,}")
c4.metric('Missing cells',f"{report['missing_cells']:,}")
if report['issues']: st.warning(' · '.join(report['issues']))
else: st.success('No structural integrity issues detected by these checks.')
if report['nonfinite_numeric_values']: st.dataframe(pd.DataFrame([{'variable':k,'nonfinite_values':v} for k,v in report['nonfinite_numeric_values'].items()]),use_container_width=True)

st.divider(); st.header('2. Longitudinal mixed-effects modelling')
numeric=list(df.select_dtypes(include='number').columns)
allcols=list(df.columns)
if len(numeric)>=2:
    a,b,c=st.columns(3)
    outcome=a.selectbox('Outcome',numeric,key='research_rs_y')
    time=b.selectbox('Time variable',[x for x in numeric if x!=outcome],key='research_rs_time')
    group=c.selectbox('Grouping variable',allcols,key='research_rs_group')
    covars=st.multiselect('Fixed-effect covariates',[x for x in allcols if x not in {outcome,time,group}],key='research_rs_covars')
    if st.button('Fit random-slope model',type='primary'):
        try:
            model,used=fit_random_slope_model(df,outcome,time,group,covars)
            st.session_state['research_random_slope_summary']=model.summary().as_text()
            st.session_state['research_random_slope_n']=len(used)
            st.session_state['research_random_slope_converged']=bool(getattr(model,'converged',False))
        except Exception as e: st.error(f'{type(e).__name__}: {e}')
    if st.session_state.get('research_random_slope_summary'):
        st.caption(f"Complete observations used: {st.session_state['research_random_slope_n']:,}")
        if st.session_state.get('research_random_slope_converged'):
            st.success('Optimizer reported convergence. Review covariance estimates and residual diagnostics before interpretation.')
        else:
            st.warning('Optimizer did not report convergence. Do not interpret inferential estimates until the model specification, scaling, sample size and optimizer have been reviewed.')
        st.code(st.session_state['research_random_slope_summary'])
else: st.info('At least two numeric variables are needed for this model.')
st.caption('Random-slope models require repeated time measurements within independent animals/groups. Check convergence, singularity, time coding and the sampling hierarchy before interpretation.')

st.divider(); st.header('3. Consensus clustering of animal phenotype profiles')
if 'animal_id' in st.session_state.get('roles',{}) and st.session_state['roles'].get('animal_id'):
    animal=st.session_state['roles']['animal_id']
else: animal=st.selectbox('Animal identifier',allcols,key='research_animal')
features=st.multiselect('Numeric phenotype variables', [x for x in numeric if x!=animal],key='research_cluster_features')
k=st.slider('Number of clusters',2,8,3,key='research_k')
resamples=st.slider('Consensus resamples',50,500,200,50,key='research_resamples')
if st.button('Run consensus clustering'):
    try:
        profiles=df[[animal]+features].copy()
        profiles[features]=profiles[features].apply(pd.to_numeric,errors='coerce')
        profiles=profiles.groupby(animal)[features].median().dropna(how='all')
        assignments,consensus=consensus_clustering(profiles,k,resamples)
        st.session_state['research_consensus_assignments']=assignments
        st.session_state['research_consensus_matrix']=consensus
    except Exception as e: st.error(f'{type(e).__name__}: {e}')
if st.session_state.get('research_consensus_assignments') is not None:
    st.dataframe(st.session_state['research_consensus_assignments'],use_container_width=True)
    st.download_button('Download consensus assignments',st.session_state['research_consensus_assignments'].to_csv(index=False),'consensus_cluster_assignments.csv','text/csv')
    st.caption('Consensus values represent the proportion of resamples in which two animal profiles co-clustered. Inspect the consensus matrix and sensitivity to cluster count/resampling settings.')

st.divider(); st.header('4. Reproducibility and provenance manifest')
analysis_name=st.text_input('Analysis name','Methane phenotype exploratory analysis')
parameters={'active_species':st.session_state.get('species'), 'dataset_name':st.session_state.get('data_name'),
            'analysis_modules_available':['random_slope_mixed_model','consensus_clustering','dataset_integrity']}
manifest=create_reproducibility_manifest(df,analysis_name,parameters,st.session_state.get('data_name'))
st.download_button('Download provenance manifest',json.dumps(manifest,indent=2,default=str),'analysis_provenance_manifest.json','application/json')
