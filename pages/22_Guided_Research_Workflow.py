import streamlit as st
st.set_page_config(page_title="Guided workflows | Methane Phenotype Analytics",page_icon="🧭",layout="wide")
from analysis_engine.ui import header, metric_row, empty_state, render_sidebar_navigation
from analysis_engine.research_intelligence import dataset_readiness, automated_recommendations
from platform_core.auth import require_principal

require_principal()
render_sidebar_navigation()
header("Guided research workflow","A structured route from raw methane measurements to validated phenotypes, robust models and reproducible outputs.",badge="RESEARCH PATHWAY")

df=st.session_state.get("data")
roles=st.session_state.get("roles",{})
definitions=st.session_state.get("phenotype_definitions",{})
has_data=df is not None
readiness=dataset_readiness(df,roles,st.session_state.get("measurement_protocol",{})) if has_data else None
animal=roles.get("animal_id")
has_animal=bool(animal and has_data and animal in df.columns)
metric_row([
    ("DATASET",st.session_state.get("data_name","None") if has_data else "None","Active research dataset"),
    ("RECORDS",f"{len(df):,}" if has_data else "0","Source observations"),
    ("ANIMALS",f"{df[animal].nunique():,}" if has_animal else "Not mapped","Unique animals"),
    ("DATA READINESS",f"{readiness['readiness_pct']:.0f}%" if readiness else "—","Metadata and structure checklist")
])

steps=[
    ("01","Study setup and data import","Select species, import data, define project and document instrument, measurement method, units and calibration.","pages/28_Research_Intelligence.py","Open study setup",has_data),
    ("02","Data profiling and quality control","Run centralised integrity, missingness, phenotype range, outlier and repeated-measure QC checks.","pages/01_Data_Quality_QC_Centre.py","Open Data Quality & QC Centre",has_data),
    ("03","Variable mapping and phenotype construction","Map animal ID, methane outcomes, covariates and sessions; document derived phenotype formulas.","pages/19_Custom_Phenotype_Builder.py","Build phenotypes",has_animal),
    ("04","Phenotype discovery and reliability","Evaluate distributions, repeatability, agreement, duration sensitivity and biological associations.","pages/21_Phenotype_Validation.py","Validate phenotypes",bool(st.session_state.get("phenotype_validation_results"))),
    ("05","Statistical inference","Use animal-aware group comparisons, mixed-effects models and robust inference where design supports them.","pages/03_Statistical_Models.py","Run statistical models",bool(st.session_state.get("statistical_model_results"))),
    ("06","Machine learning and multivariate analysis","Compare models using animal-grouped validation; assess clustering and PCA as exploratory analyses.","pages/04_ML_Benchmarking.py","Benchmark models",bool(st.session_state.get("ml_benchmark_results") or st.session_state.get("nested_ml_results"))),
    ("07","Longitudinal and robustness assessment","Assess within-animal trajectories, emitter transitions and sensitivity to thresholds and assumptions.","pages/10_Longitudinal_Analysis.py","Open longitudinal analysis",bool(st.session_state.get("longitudinal_results"))),
    ("08","Publication and reproducibility","Generate scientific tables, figures, methods notes, manifests and compare analysis runs.","pages/27_Scientific_Publication_Suite.py","Generate research outputs",bool(st.session_state.get("publication_bundle"))),
]
completed=sum(bool(x[5]) for x in steps)
st.subheader("Research pathway")
st.progress(completed/len(steps))
st.caption(f"{completed} of {len(steps)} workflow indicators currently satisfied. Completion is indicative and does not certify scientific validity.")
cols=st.columns(2)
for i,(num,title,desc,target,action,done) in enumerate(steps):
    with cols[i%2]:
        with st.container(border=True):
            st.markdown(f"**STEP {num} · {'INDICATOR MET' if done else 'PENDING'}**")
            st.subheader(title)
            st.write(desc)
            st.page_link(target,label=action,icon="✅" if done else "➡️",use_container_width=True)

st.divider()
left,right=st.columns([1.1,.9])
with left:
    st.subheader("Recommended next analyses")
    if has_data:
        for rec in automated_recommendations(df,roles)[:6]:
            st.markdown(f"**{rec['priority']} — {rec['analysis']}**")
            st.caption(rec["reason"])
    else:
        st.info("Import a dataset to receive study-specific recommendations.")
with right:
    st.subheader("Scientific guardrails")
    st.info("Keep repeated observations from the same animal together in model validation. Record-level random splits can create leakage and optimistic performance estimates.")
    st.warning("Sensor concentration, AUC and other instrument signals are not methane mass flux (e.g. g/day) without a validated calibration model.")
    st.caption("Treat clusters as exploratory until stability and external biological validity have been demonstrated.")
if not has_data:
    empty_state("No active dataset yet","Import a CSV, Parquet or Excel dataset from the sidebar to begin the research pathway.")
