import streamlit as st
import pandas as pd
from analysis_engine.ui import header, metric_row
from platform_core.auth import require_principal
from platform_core.database import configured
from platform_core.workspace import list_projects, create_project, save_dataset, list_datasets, load_dataset
from platform_core.species import PROFILES
from platform_core.data_governance import inspect_dataset

from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

principal=require_principal()
header('Project workspace','Manage tenant-scoped livestock studies, datasets and species-specific metadata.')
if not configured():
    st.warning('Persistent project workspace is not connected. Configure DATABASE_URL and apply database/schema.sql. The local research workflow remains available from the sidebar.')
    st.stop()
try:
    projects=list_projects(principal.tenant_id,principal.subject)
except Exception as exc:
    st.error(f'Unable to load projects: {exc}')
    st.stop()

with st.expander('Create a research project',expanded=not bool(projects)):
    with st.form('create_project_form'):
        name=st.text_input('Project name')
        species_label=st.selectbox('Livestock species',[p.label for p in PROFILES.values()])
        description=st.text_area('Description / study objective')
        submit=st.form_submit_button('Create project')
    if submit:
        if not name.strip(): st.error('Enter a project name.')
        else:
            try:
                species=next(p.key for p in PROFILES.values() if p.label==species_label)
                create_project(principal.tenant_id,principal.subject,name.strip(),species,description.strip())
                st.success('Project created.')
                st.rerun()
            except Exception as exc: st.error(str(exc))

if not projects:
    st.info('No projects are available to your account yet. Create a project or ask a tenant administrator to grant project access.')
    st.stop()
project_labels={f"{p['name']} · {p['species'].title()} · {p['id'][:8]}":p for p in projects}
selected_label=st.selectbox('Active project',list(project_labels))
project=project_labels[selected_label]
st.session_state['active_project_id']=project['id']
st.session_state['active_project_species']=project['species']
st.session_state['species']=project['species']

st.subheader('Upload a dataset to this project')
with st.expander('Measurement protocol metadata',expanded=True):
    p1,p2=st.columns(2)
    with p1:
        instrument=st.text_input('Instrument / measurement system',key='upload_instrument')
        method=st.selectbox('Measurement method',['Not specified','Respiration chamber','GreenFeed','Laser methane detector','Portable accumulation chamber','Breath sampling','Other'],key='upload_method')
        units=st.text_input('Methane variable units',key='upload_units')
    with p2:
        calibration=st.selectbox('Calibration status',['Not documented','Manufacturer calibration only','Study-specific validated calibration','Not applicable / presence-only signal'],key='upload_calibration')
        sop=st.text_input('Protocol / SOP reference',key='upload_sop')
        min_duration=st.number_input('Minimum valid recording duration (seconds)',min_value=0.0,value=0.0,step=10.0,key='upload_min_duration')
protocol={'instrument':instrument,'method':method,'units':units,'calibration_status':calibration,'protocol_reference':sop,'minimum_recording_duration_seconds':min_duration}
up=st.file_uploader('Upload dataset (CSV or Parquet)',type=['csv','parquet','pq','xlsx','xls'],help='CSV and Parquet are supported. Excel remains available for backward compatibility. All new project datasets are stored internally as Parquet.',key='persistent_dataset_upload')
if up is not None:
    try:
        raw=up.getvalue()
        from analysis_engine.io import load_uploaded_data
        df=load_uploaded_data(up)
        profile=inspect_dataset(df,project['species'])
        metric_row([('RECORDS',f"{len(df):,}",'Rows detected'),('VARIABLES',str(df.shape[1]),'Columns detected'),('UNIQUE ANIMALS',str(profile['n_animals'] if profile['n_animals'] is not None else 'Not mapped'),'Species adapter inference')])
        st.json({'species':project['species'],'candidate_roles':profile['roles'],'missing_percent':profile['missing_percent'],'duplicate_rows':profile['duplicate_rows']})
        if st.button('Save dataset to project storage',type='primary'):
            result=save_dataset(principal.tenant_id,principal.subject,project['id'],up.name,raw,df,project['species'],protocol)
            st.success(f"Dataset saved in canonical Parquet format. Storage SHA-256: {result['sha256']}")
            st.caption(f"Original upload: {result['source_format'].upper()} · Internal storage: PARQUET · Records: {len(df):,}")
    except Exception as exc: st.error(f'Dataset validation/upload failed: {exc}')

st.subheader('Project datasets')
try:
    datasets=list_datasets(principal.tenant_id,project['id'],principal.subject)
    if datasets:
        st.dataframe(pd.DataFrame(datasets),use_container_width=True,hide_index=True)
        opts={f"{d['name']} · {d['row_count']:,} rows · {d['created_at']}":d for d in datasets}
        choice=st.selectbox('Load a stored dataset into the analysis workspace',list(opts))
        if st.button('Load selected dataset',type='primary'):
            df,name,species=load_dataset(principal.tenant_id,project['id'],opts[choice]['id'],principal.subject)
            st.session_state['data']=df;st.session_state['raw_data_snapshot']=df.copy(deep=True);st.session_state['cleaning_log']=[]
            st.session_state['data_name']=name;st.session_state['species']=species
            from platform_core.species import infer_species_roles
            st.session_state['roles']=infer_species_roles(df.columns,species)
            st.session_state['active_dataset_id']=opts[choice]['id']
            st.success('Dataset loaded into the analysis workspace. Open the analytical modules from the sidebar.')
    else: st.info('No datasets have been uploaded to this project yet.')
except Exception as exc: st.error(f'Unable to retrieve project datasets: {exc}')
