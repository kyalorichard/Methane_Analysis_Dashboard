import streamlit as st
import os
import pandas as pd
import numpy as np
from pathlib import Path
from analysis_engine.io import load_uploaded_data, validate_dataset, infer_roles
from analysis_engine.metrics import dataset_profile
from analysis_engine.plots import missingness_plot, correlation_plot, numeric_distribution
from analysis_engine.ui import apply_style, header, metric_row
from platform_core.auth import require_principal, tenant_memberships_for_subject
from platform_core.species import infer_species_roles, PROFILES
from platform_core.data_governance import inspect_dataset, validate_species_dataset
from platform_core.database import configured
from platform_core import storage

st.set_page_config(page_title='Methane Phenotype Analytics',page_icon='🐑',layout='wide',initial_sidebar_state='expanded')
apply_style()
principal = require_principal()
st.session_state['user_id'] = principal.subject
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

def progress_step(label, completed, description=""):
    """Display an analysis-readiness step in the sidebar."""
    icon = "✓" if completed else "○"
    status = "Complete" if completed else "Pending"

    with st.container():
        col1, col2 = st.columns([0.12, 0.88])

        with col1:
            st.markdown(
                f"<div style='font-size:18px;color:"
                f"{'#16A34A' if completed else '#9CA3AF'};"
                f"font-weight:700'>{icon}</div>",
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"**{label}**  "
                f"<span style='font-size:11px;color:"
                f"{'#16A34A' if completed else '#9CA3AF'}'>"
                f"{status}</span>",
                unsafe_allow_html=True
            )
            if description:
                st.caption(description)

def activate(df,name,species='Sheep'):
    st.session_state['data']=df
    st.session_state['raw_data_snapshot']=df.copy(deep=True)
    st.session_state['cleaning_log']=[]
    st.session_state['data_name']=name
    st.session_state['roles']=infer_species_roles(df.columns,species)
    st.session_state['species']=species
    st.session_state['dataset_profile']=inspect_dataset(df,species)
    from analysis_engine.research_intelligence import dataframe_fingerprint
    fingerprint=dataframe_fingerprint(df)[:16]
    catalogue=st.session_state.setdefault('dataset_catalogue',{})
    catalogue[fingerprint]={'name':name,'data':df.copy(),'species':species}
    st.session_state['active_dataset_key']=fingerprint

# Use the same compact grouped navigation on the landing page and every analysis page.
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

with st.sidebar:
    st.markdown("<div class='section-kicker'>Workspace controls</div>",unsafe_allow_html=True)
    species_labels={p.label:p.key for p in PROFILES.values()}
    selected_species=st.selectbox('Livestock species',list(species_labels),index=list(species_labels.values()).index(st.session_state.get('species','sheep')) if st.session_state.get('species','sheep') in species_labels.values() else 0,key='species_selector')
    st.session_state['species']=species_labels[selected_species]
    st.markdown("<div class='section-kicker'>Dataset</div>",unsafe_allow_html=True)
    upload=st.file_uploader('Import phenotype dataset',type=['csv','parquet','pq','xlsx','xls'],help='Upload CSV, Parquet or Excel data.')
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
            st.session_state['data']=item['data']; st.session_state['data_name']=item['name']; st.session_state['species']=item['species']
            st.session_state['roles']=infer_species_roles(item['data'].columns,item['species']); st.session_state['active_dataset_key']=selected_key
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
    st.divider(); st.caption(f"Signed in: {principal.email} • {principal.role}"); st.caption(f"Tenant: {principal.tenant_id} • {principal.auth_source}")

header('Methane Phenotype Analytics','A reproducible workspace for methane phenotype quality control, statistical inference and predictive modelling.')
if 'data' not in st.session_state:
    st.markdown("<div class='hero'><span class='tag'>RESEARCH WORKSPACE</span><h1>Methane Phenotype Analytics</h1><p>A guided scientific environment for measurement quality, phenotype discovery, statistical inference, machine learning and reproducible livestock methane research.</p></div>",unsafe_allow_html=True)
    st.subheader("Start a research session")
    st.write("Import a study dataset from the sidebar or load the example sheep dataset. The research command centre will profile the data and recommend suitable next steps.")
    a,b,c=st.columns(3)
    with a: st.markdown("<div class='workflow-card'><div class='step'>01 · DATA & MEASUREMENT</div><h3>Establish data readiness</h3><p>Map animal identifiers, methane outcomes, recording duration, measurement units, instrument and calibration metadata.</p></div>",unsafe_allow_html=True)
    with b: st.markdown("<div class='workflow-card'><div class='step'>02 · PHENOTYPE EVIDENCE</div><h3>Evaluate candidate traits</h3><p>Assess distributions, missingness, repeatability, duration sensitivity, biological associations and robustness.</p></div>",unsafe_allow_html=True)
    with c: st.markdown("<div class='workflow-card'><div class='step'>03 · MODELLING & REPORTING</div><h3>Build reproducible evidence</h3><p>Compare conventional and animal-grouped ML approaches, validate findings and export research outputs.</p></div>",unsafe_allow_html=True)
    st.markdown("### Research workflow")
    st.page_link("pages/28_Research_Intelligence.py",label="Open research command centre",icon="🧭",use_container_width=True)
    st.page_link("pages/22_Guided_Research_Workflow.py",label="Open guided research workflow",icon="🗺️",use_container_width=True)
    st.page_link("pages/23_Integrated_Analysis_Centre.py",label="Run integrated analysis",icon="🧪",use_container_width=True)
    st.markdown("<div class='panel'><b>Scientific guardrails</b><p class='muted'>Keep repeated observations from the same animal together during model validation. Sensor concentration and AUC are not methane mass flux (e.g. g/day) without validated calibration. Flagged observations require review; automated QC must not silently remove records.</p></div>",unsafe_allow_html=True)
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

# Executive research dashboard: distinguish records from independent animals.
n_animals = int(df[animal].nunique()) if animal and animal in df.columns else None
repeated_animals = int((df.groupby(animal).size() >= 2).sum()) if animal and animal in df.columns else None
n_rounds = int(df[round_col].nunique()) if round_col and round_col in df.columns else None
dup_rows = int(df.duplicated().sum())
numeric_frame = df.select_dtypes(include="number")
nonfinite = int(np.isinf(numeric_frame.to_numpy(dtype=float, na_value=np.nan)).sum()) if not numeric_frame.empty else 0
st.subheader("Study structure")
s1, s2, s3, s4 = st.columns(4)
s1.metric("Repeated animals", f"{repeated_animals:,}" if repeated_animals is not None else "Not mapped", help="Animals with at least two records; not necessarily complete across all rounds.")
s2.metric("Measurement rounds", f"{n_rounds:,}" if n_rounds is not None else "Not mapped")
s3.metric("Exact duplicate rows", f"{dup_rows:,}")
s4.metric("Non-finite numeric cells", f"{nonfinite:,}")
q1, q2 = st.columns([1.2, 1])
with q1:
    st.markdown("**Recommended next actions**")
    st.page_link("pages/01_Data_Management.py", label="Review data quality and variable mapping", icon="🧹")
    st.page_link("pages/16_Species_Protocol_Configuration.py", label="Confirm species and measurement protocol", icon="🐑")
    st.page_link("pages/33_Reliability_and_Agreement.py", label="Assess repeatability and measurement agreement", icon="📏")
    st.page_link("pages/34_Advanced_ML_Explainability.py", label="Run animal-grouped predictive validation", icon="🤖")
with q2:
    st.markdown("**Interpretation safeguards**")
    st.caption("• The animal is usually the independent biological unit, not each measurement row.")
    st.caption("• Repeated measurements must remain grouped during model validation.")
    st.caption("• Sensor concentration and AUC are not methane mass flux without validated calibration.")
    st.caption("• QC flags should prompt review; do not silently delete observations.")
from analysis_engine.research_intelligence import dataset_readiness
readiness=dataset_readiness(df,roles,st.session_state.get("measurement_protocol",{}))
st.subheader("Research readiness")
rc1,rc2=st.columns([1,3])
readiness_pct=readiness["readiness_pct"]
rc1.metric("Readiness checklist",f"{readiness_pct:.0f}%")
rc2.progress(readiness_pct/100)
st.caption("Checklist covers mapped identifiers, outcome, measurement metadata, recording structure and duplicate rows; it is not a scientific certification.")
st.page_link("pages/28_Research_Intelligence.py",label="Open research command centre for QC, calibration and phenotype evidence",icon="🧭")
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
