import streamlit as st
import os
import pandas as pd
from pathlib import Path
from analysis_engine.io import load_uploaded_data, validate_dataset, infer_roles
from analysis_engine.metrics import dataset_profile
from analysis_engine.plots import missingness_plot, correlation_plot, numeric_distribution
from analysis_engine.ui import apply_style, header, metric_row
from platform_core.auth import require_principal, tenant_memberships_for_subject
from platform_core.species import infer_species_roles, PROFILES
from platform_core.data_governance import inspect_dataset, validate_species_dataset
from platform_core.database import configured
from platform_core.workspace import list_projects

st.set_page_config(page_title='Methane Phenotype Analytics',page_icon='🐑',layout='wide',initial_sidebar_state='expanded')
apply_style()
principal = require_principal()
if os.getenv('AUTH_MODE','development').lower() == 'entra_proxy':
    memberships = tenant_memberships_for_subject(principal.subject)
    if len(memberships) > 1:
        tenant_options = {m['tenant_name']: m['tenant_id'] for m in memberships}
        with st.sidebar:
            selected_tenant = st.selectbox('Institutional workspace', list(tenant_options), index=list(tenant_options.values()).index(principal.tenant_id), key='tenant_workspace_selector')
        if tenant_options[selected_tenant] != principal.tenant_id:
            st.session_state['active_tenant_id'] = tenant_options[selected_tenant]
            st.rerun()

DATA_PATH=Path(__file__).parent/'data'/'ICARDA_sheep_methane_phenotypes.csv'

def activate(df,name,species='Sheep'):
    st.session_state['data']=df
    st.session_state['raw_data_snapshot']=df.copy(deep=True)
    st.session_state['cleaning_log']=[]
    st.session_state['data_name']=name
    st.session_state['roles']=infer_species_roles(df.columns,species)
    st.session_state['species']=species
    st.session_state['dataset_profile']=inspect_dataset(df,species)
    import hashlib
    fingerprint=hashlib.sha256((str(name)+str(df.shape)+str(list(df.columns))).encode()).hexdigest()[:12]
    catalogue=st.session_state.setdefault('dataset_catalogue',{})
    catalogue[fingerprint]={'name':name,'data':df.copy(),'species':species}
    st.session_state['active_dataset_key']=fingerprint

with st.sidebar:
    st.markdown("<div class='brand-lockup'><div class='brand-mark'>M</div><div><div class='brand-name'>Methane Phenotype<br>Analytics</div><div class='brand-sub'>ICARDA research workspace</div></div></div>",unsafe_allow_html=True)
    st.caption("Research workspace")
    st.divider()

    st.markdown("<div class='nav-group-label'>Workspace</div>",unsafe_allow_html=True)
    st.page_link("app.py", label="Overview", icon="🏠")
    st.page_link("pages/22_Guided_Research_Workflow.py", label="Guided workflow", icon="🧭")
    st.page_link("pages/00_Project_Workspace.py", label="Projects & datasets", icon="🗂️")

    st.markdown("<div class='nav-group-label'>Data preparation</div>",unsafe_allow_html=True)
    st.page_link("pages/01_Data_Management.py", label="Data management & QC", icon="🧹")
    st.page_link("pages/16_Species_Protocol_Configuration.py", label="Species & protocol", icon="🐑")
    st.page_link("pages/19_Custom_Phenotype_Builder.py", label="Phenotype builder", icon="🧬")

    st.markdown("<div class='nav-group-label'>Explore & validate</div>",unsafe_allow_html=True)
    st.page_link("pages/02_Descriptive_Analysis.py", label="Descriptive analysis", icon="📊")
    st.page_link("pages/06_Phenotype_Analysis.py", label="Phenotype analysis", icon="🔬")
    st.page_link("pages/07_Repeatability_Reliability.py", label="Repeatability", icon="🔁")
    st.page_link("pages/08_Group_Comparisons.py", label="Group comparisons", icon="⚖️")
    st.page_link("pages/21_Phenotype_Validation.py", label="Phenotype validation", icon="✅")
    st.page_link("pages/18_Low_High_Emitter_Reports.py", label="Low / high emitters", icon="↕️")
    st.page_link("pages/20_Longitudinal_Emitter_Tracking.py", label="Emitter tracking", icon="📈")

    st.markdown("<div class='nav-group-label'>Model & explain</div>",unsafe_allow_html=True)
    st.page_link("pages/03_Statistical_Models.py", label="Statistical models", icon="📐")
    st.page_link("pages/04_ML_Benchmarking.py", label="ML benchmarking", icon="🤖")
    st.page_link("pages/05_Clustering_PCA.py", label="Clustering & PCA", icon="🧩")
    st.page_link("pages/09_Explainability.py", label="Model explainability", icon="💡")
    st.page_link("pages/10_Longitudinal_Analysis.py", label="Longitudinal analysis", icon="🗓️")
    st.page_link("pages/11_Advanced_Analysis.py", label="Advanced analysis", icon="🧪")
    st.page_link("pages/12_Sensitivity_Robustness.py", label="Sensitivity & robustness", icon="🛡️")
    st.page_link("pages/13_Equivalence_Analysis.py", label="Equivalence analysis", icon="↔️")
    st.page_link("pages/14_Phenotype_Scorecard.py", label="Phenotype scorecard", icon="🏅")
    st.page_link("pages/17_Scientific_Analysis_Workbench.py", label="Scientific workbench", icon="🧰")

    st.markdown("<div class='nav-group-label'>Outputs</div>",unsafe_allow_html=True)
    st.page_link("pages/15_Reports_Exports.py", label="Reports & exports", icon="📄")
    st.page_link("pages/27_Scientific_Publication_Suite.py", label="Publication suite", icon="📚")

    st.divider()
    st.markdown("<div class='section-kicker'>Project selector</div>",unsafe_allow_html=True)
    if configured():
        try:
            available_projects=list_projects(principal.tenant_id,principal.subject)
            if available_projects:
                project_options={f"{p['name']} · {p['species'].title()}":p for p in available_projects}
                project_labels=list(project_options)
                active_id=st.session_state.get('active_project_id')
                default_project=next((label for label,pj in project_options.items() if pj['id']==active_id),project_labels[0])
                chosen_project=st.selectbox("Active project",project_labels,index=project_labels.index(default_project),key="sidebar_project_selector")
                selected_project=project_options[chosen_project]
                st.session_state['active_project_id']=selected_project['id']
                st.session_state['active_project_species']=selected_project['species']
            else:
                st.caption("No accessible projects yet. Create one in Projects & datasets.")
        except Exception:
            st.caption("Project selector unavailable; open Projects & datasets to configure access.")
    else:
        st.caption("Local research session · persistent projects not configured")
    species_labels={p.label:p.key for p in PROFILES.values()}
    selected_species=st.selectbox('Livestock species',list(species_labels),index=list(species_labels.values()).index(st.session_state.get('species','sheep')) if st.session_state.get('species','sheep') in species_labels.values() else 0,key='species_selector')
    st.session_state['species']=species_labels[selected_species]

    st.markdown("<div class='section-kicker'>Dataset selector</div>",unsafe_allow_html=True)
    upload=st.file_uploader('Import phenotype dataset',type=['csv','parquet','pq','xlsx','xls'],help='Upload CSV or Parquet (also Excel for backward compatibility). Data is loaded into the research session; project storage uses canonical Parquet.')
    if upload is not None:
        try:
            activate(load_uploaded_data(upload),upload.name,species_labels[selected_species])
            st.success('Dataset loaded')
        except Exception as e: st.error(f'Unable to load dataset: {e}')
    if st.button('Load example sheep dataset',use_container_width=True):
        activate(pd.read_csv(DATA_PATH),DATA_PATH.name,'sheep');st.rerun()

    catalogue=st.session_state.get('dataset_catalogue',{})
    if catalogue:
        keys=list(catalogue)
        labels={f"{catalogue[k]['name']} · {catalogue[k]['species'].title()}":k for k in keys}
        current=st.session_state.get('active_dataset_key')
        default_label=next((label for label,key in labels.items() if key==current),list(labels)[0])
        selected_label=st.selectbox('Switch active dataset',list(labels),index=list(labels).index(default_label),key='dataset_switcher')
        selected_key=labels[selected_label]
        if selected_key != current:
            item=catalogue[selected_key]
            st.session_state['data']=item['data']
            st.session_state['data_name']=item['name']
            st.session_state['species']=item['species']
            st.session_state['roles']=infer_species_roles(item['data'].columns,item['species'])
            st.session_state['active_dataset_key']=selected_key
            st.rerun()
        st.success(f"Active · {len(st.session_state['data']):,} records")
        st.caption(st.session_state.get('data_name','Dataset loaded'))
        if st.button('Clear active dataset',use_container_width=True):
            for k in ['data','data_name','roles','dataset_profile','active_dataset_key']: st.session_state.pop(k,None)
            st.rerun()
    else:
        st.info('Import a dataset or load the example dataset to begin.')

    st.markdown("<div class='section-kicker'>Analysis readiness</div>",unsafe_allow_html=True)
    has_data='data' in st.session_state
    mapped=bool(st.session_state.get('roles',{}).get('animal_id')) if has_data else False
    has_derived=bool(st.session_state.get('phenotype_definitions')) if has_data else False
    progress_step('Dataset imported',has_data,'Ready to inspect' if has_data else 'Import a CSV or Parquet file')
    progress_step('Animal ID mapped',mapped,'Needed for animal-level validation' if mapped else 'Map Animal ID in Data management')
    progress_step('Derived phenotypes',has_derived,'Formula registry available' if has_derived else 'Optional: create a phenotype')
    st.divider()
    st.caption(f"Signed in: {principal.email} • {principal.role}")
    st.caption(f"Tenant: {principal.tenant_id} • {principal.auth_source}")

header('Methane Phenotype Analytics','A reproducible workspace for methane phenotype quality control, statistical inference and predictive modelling.')
if 'data' not in st.session_state:
    st.markdown("<div class='hero'><span class='tag'>RESEARCH WORKSPACE</span><h1>Welcome to Methane Phenotype Analytics</h1><p>A guided environment for livestock methane phenotype quality control, scientific evaluation, statistical modelling and reproducible research.</p></div>",unsafe_allow_html=True)
    st.markdown('### Get started')
    st.write('Import your study dataset from the left panel, or load the included example dataset to explore the platform. You can change species and map study variables after importing.')
    a,b,c=st.columns(3)
    with a: st.markdown("<div class='workflow-card'><div class='step'>01 · Import</div><h3>Bring in your data</h3><p>Upload CSV or Excel files, select the livestock species and map animal, breed, round and phenotype variables.</p></div>",unsafe_allow_html=True)
    with b: st.markdown("<div class='workflow-card'><div class='step'>02 · Explore</div><h3>Check data quality</h3><p>Review missingness, distributions, recording quality, repeated observations and candidate phenotype definitions.</p></div>",unsafe_allow_html=True)
    with c: st.markdown("<div class='workflow-card'><div class='step'>03 · Analyse</div><h3>Build scientific evidence</h3><p>Compare conventional and machine-learning methods, assess repeatability and export transparent results.</p></div>",unsafe_allow_html=True)
    st.markdown('')
    left,right=st.columns([1.15,.85])
    with left:
        st.markdown('#### Recommended analysis sequence')
        st.markdown('1. **Data management** — inspect records and map study variables.\n2. **Descriptive analysis** — assess phenotype distributions and group structure.\n3. **Phenotype development** — define derived traits using documented formulas.\n4. **Scientific validation** — assess repeatability, association and biological plausibility.\n5. **Modelling** — benchmark conventional and machine-learning approaches using animal-grouped validation.\n6. **Reporting** — export datasets, tables and reproducibility metadata.')
    with right:
        st.markdown("<div class='panel'><div class='section-kicker'>Research principles</div><b>Animal-level validation</b><p class='muted'>Repeated observations from the same animal should remain together during model validation.</p><hr><b>Transparent phenotype definitions</b><p class='muted'>Record formulas, units, assumptions and protocol context for derived variables.</p><hr><b>Interpretation with care</b><p class='muted'>Sensor signals and AUC measures are not methane mass flux without validated calibration.</p></div>",unsafe_allow_html=True)
    st.stop()

df=st.session_state['data']; prof=dataset_profile(df); roles=st.session_state.get('roles',infer_roles(df))
animal=roles.get('animal_id'); breed=roles.get('breed'); round_col=roles.get('round')
header('Dataset overview',f"{st.session_state.get('data_name','Active dataset')}  •  Species: {st.session_state.get('species','sheep').title()}")
profile=inspect_dataset(df,st.session_state.get('species','sheep'))
with st.expander('Species adapter and protocol readiness'):
    st.write(profile['species_adapter_note'])
    for issue in validate_species_dataset(df,st.session_state.get('species','sheep')): st.warning(issue)
    st.caption('Species-specific phenotype semantics, units, calibration and QC limits must be confirmed by the study team before cross-species comparisons.')
metric_row([('RECORDS',f"{len(df):,}",'Rows in active dataset'),('VARIABLES',f"{df.shape[1]:,}",'Columns in active dataset'),('UNIQUE ANIMALS',f"{df[animal].nunique():,}" if animal in df else 'Not mapped','Distinct animal identifiers'),('MISSING CELLS',f"{prof['missing_percent']:.2f}%",'Percentage of all cells missing')])
left,right=st.columns([1.25,1])
with left:
    st.subheader('Phenotype distribution')
    candidate=[c for c in ['mean_methane','AUC_full','AUC_peaks','AUC_per_sec'] if c in df.columns]
    nums=df.select_dtypes('number').columns.tolist()
    if nums:
        y=st.selectbox('Numeric phenotype / variable',candidate or nums,key='overview_y')
        fig=numeric_distribution(df,y);st.plotly_chart(fig,use_container_width=True)
with right:
    st.subheader('Missingness by variable')
    st.plotly_chart(missingness_plot(df),use_container_width=True)
    st.subheader('Dataset quality checks')
    issues=validate_dataset(df)
    checks=[('No exact duplicate rows',df.duplicated().sum()==0,f"{df.duplicated().sum()} duplicate rows"),('Animal ID detected',bool(animal),str(animal or 'Map in Data Management')),('Methane variable detected',bool(roles.get('methane')),str(roles.get('methane') or 'Map in Data Management'))]
    for label,ok,detail in checks:
        st.write(('✅' if ok else '⚠️')+f' **{label}** — {detail}')
if len(nums)>1:
    st.subheader('Numeric variable correlation')
    st.plotly_chart(correlation_plot(df[nums[:min(18,len(nums))]]),use_container_width=True)
st.info('Scientific note: sensor-derived methane concentration and AUC are phenotype signal proxies. Do not report them as methane mass flux (e.g. g/day) without a validated calibration model. Repeated animal records must remain grouped in validation.')
