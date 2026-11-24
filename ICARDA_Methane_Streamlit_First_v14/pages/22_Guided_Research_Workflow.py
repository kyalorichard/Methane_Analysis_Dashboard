import streamlit as st
st.set_page_config(page_title="Guided workflows | Methane Phenotype Analytics",page_icon="🧭",layout="wide")
from analysis_engine.ui import header, metric_row, progress_step, empty_state, render_sidebar_navigation
from platform_core.auth import require_principal

require_principal()
render_sidebar_navigation()
header("Guided research workflow","A practical route from raw livestock measurements to validated phenotypes and reproducible scientific outputs.",badge="GETTING STARTED")

df=st.session_state.get("data")
roles=st.session_state.get("roles",{})
definitions=st.session_state.get("phenotype_definitions",{})
has_data=df is not None
animal=roles.get("animal_id")
has_animal=bool(animal and has_data and animal in df.columns)
n_steps=4
complete=sum([has_data,has_animal,bool(definitions),bool(st.session_state.get("analysis_completed"))])
metric_row([
    ("WORKFLOW COMPLETION",f"{complete}/{n_steps}","Indicative progress; steps can be completed in any order"),
    ("ACTIVE DATASET",st.session_state.get("data_name","None") if has_data else "None","Current analysis dataset"),
    ("ANIMALS",f"{df[animal].nunique():,}" if has_animal else "Not mapped","Unique animal identifiers"),
    ("CUSTOM PHENOTYPES",str(len(definitions)),"Definitions in this session")
])

st.subheader("Your research pathway")
steps=[
    ("01","Import and profile data","Load a CSV or Excel dataset, select the livestock species, inspect missingness and duplicates.","pages/01_Data_Management.py","Open data management",has_data),
    ("02","Map study variables","Identify animal ID, breed, sex, weight, recording round, date and methane phenotype variables.","pages/01_Data_Management.py","Map variables",has_animal),
    ("03","Develop and validate phenotypes","Document formulas and units, then assess distributions, repeatability, associations and robustness.","pages/19_Custom_Phenotype_Builder.py","Build a phenotype",bool(definitions)),
    ("04","Model and report findings","Compare conventional and ML models using animal-grouped validation, explain model behaviour and export results.","pages/04_ML_Benchmarking.py","Benchmark models",bool(st.session_state.get("analysis_completed")))
]
cols=st.columns(2)
for i,(num,title,desc,target,action,done) in enumerate(steps):
    with cols[i%2]:
        st.markdown(f"""<div class='workflow-card'><div class='step'>STEP {num} · {'COMPLETED' if done else 'TO DO'}</div><h3>{title}</h3><p>{desc}</p></div>""",unsafe_allow_html=True)
        st.page_link(target,label=action,icon="✅" if done else "➡️")

st.divider()
left,right=st.columns([1.1,.9])
with left:
    st.subheader("Quick access")
    q1,q2=st.columns(2)
    with q1:
        st.page_link("pages/02_Descriptive_Analysis.py",label="Descriptive analysis",icon="📊",use_container_width=True)
        st.page_link("pages/07_Repeatability_Reliability.py",label="Repeatability & reliability",icon="🔁",use_container_width=True)
        st.page_link("pages/21_Phenotype_Validation.py",label="Phenotype validation",icon="✅",use_container_width=True)
    with q2:
        st.page_link("pages/04_ML_Benchmarking.py",label="ML benchmarking",icon="🤖",use_container_width=True)
        st.page_link("pages/05_Clustering_PCA.py",label="Clustering & PCA",icon="🧩",use_container_width=True)
        st.page_link("pages/15_Reports_Exports.py",label="Reports & exports",icon="📄",use_container_width=True)
with right:
    st.subheader("Scientific guardrails")
    st.info("Keep repeated observations from the same animal together during model validation. Random record-level splits can produce leakage and optimistic performance estimates.")
    st.warning("Sensor concentration and AUC measurements are not methane mass flux (for example, g/day) unless supported by an appropriate validated calibration.")
    st.caption("Treat clustering as exploratory unless cluster stability and external biological validity have been demonstrated.")

if not has_data:
    empty_state("No active dataset yet","Start by importing your study data or loading the example dataset from the sidebar. The workflow will become available as soon as a dataset is active.")
