import streamlit as st
import pandas as pd
import plotly.express as px
from analysis_engine.ui import header, render_sidebar_navigation, empty_state
from analysis_engine.research_hardening import grouped_classification_benchmark, fit_mixed_effects, configurable_qc
from platform_core.auth import require_principal

st.set_page_config(page_title="Research model lab | Methane Phenotype Analytics",page_icon="🧬",layout="wide")
require_principal(); render_sidebar_navigation()
header("Research model lab","Animal-grouped classification, mixed-effects modelling and configurable quality-control rules.",badge="RESEARCH HARDENING")
df=st.session_state.get("data")
if df is None: empty_state("No active dataset","Load a dataset in Project Workspace."); st.stop()
cols=df.columns.tolist(); numeric=df.select_dtypes(include="number").columns.tolist()
if not numeric: st.error("No numeric outcome variables are available."); st.stop()
roles=st.session_state.get("roles",{}); animal_default=roles.get("animal_id") if roles.get("animal_id") in cols else None
st.subheader("1. Animal-grouped classification benchmark")
st.caption("All records from the same animal are kept in the same cross-validation fold. Imputation, scaling and encoding are fitted within each training fold.")
c1,c2,c3=st.columns(3)
with c1: target=st.selectbox("Categorical target",[c for c in cols if c not in numeric],key="class_target") if any(c not in numeric for c in cols) else st.selectbox("Categorical target",numeric,key="class_target_numeric")
with c2: animal=st.selectbox("Animal identifier",cols,index=cols.index(animal_default) if animal_default else 0,key="class_animal")
with c3: nfold=st.selectbox("Grouped CV folds",[3,4,5],index=2,key="class_folds")
features=st.multiselect("Predictors",[c for c in cols if c not in {target,animal}],default=[c for c in numeric if c not in {target,animal}][:5],key="class_features")
models=st.multiselect("Classifiers",["Logistic Regression","Random Forest","Extra Trees","HistGradientBoosting"],default=["Logistic Regression","Random Forest","Extra Trees"],key="class_models")
if st.button("Run grouped classification",type="primary",key="run_classification"):
    try:
        scores,matrices,labels=grouped_classification_benchmark(df,target,features,animal,models,nfold)
        st.session_state["class_results"]=(scores,matrices,labels)
        st.success("Grouped classification benchmark completed.")
    except Exception as e: st.error(f"Classification could not be completed: {e}")
if "class_results" in st.session_state:
    scores,matrices,labels=st.session_state["class_results"]
    st.dataframe(scores,use_container_width=True,hide_index=True)
    for name,matrix in matrices.items():
        st.markdown(f"**{name} — pooled out-of-fold confusion matrix**")
        st.dataframe(matrix,use_container_width=True)
    st.caption("ROC-AUC is intentionally not reported until class-probability alignment and fold-level class support are fully validated. Accuracy alone is not sufficient under class imbalance.")
st.divider(); st.subheader("2. Repeated-measures mixed-effects model")
st.caption("Gaussian linear mixed model with animal-level random intercept. Use this when repeated observations per animal are scientifically relevant; check convergence and model assumptions.")
c1,c2,c3=st.columns(3)
with c1: outcome=st.selectbox("Numeric outcome",numeric,key="mixed_outcome")
with c2: animal_m=st.selectbox("Grouping variable (animal)",cols,index=cols.index(animal_default) if animal_default else 0,key="mixed_animal")
with c3: session=st.selectbox("Optional session / round",["— None —"]+cols,key="mixed_session")
fixed=st.multiselect("Fixed-effect predictors",[c for c in cols if c not in {outcome,animal_m}],key="mixed_fixed")
if st.button("Fit mixed-effects model",type="primary",key="fit_mixed"):
    try:
        estimates,summary=fit_mixed_effects(df,outcome,animal_m,fixed,None if session.startswith("—") else session)
        st.session_state["mixed_results"]=(estimates,summary); st.success("Mixed-effects model fitted.")
    except Exception as e: st.error(f"Model could not be fitted: {e}")
if "mixed_results" in st.session_state:
    est,summ=st.session_state["mixed_results"]; st.json(summ); st.dataframe(est,use_container_width=True,hide_index=True)
st.divider(); st.subheader("3. Configurable phenotype QC")
st.caption("Set study- or instrument-specific thresholds. These are user-defined screening rules, not universal biological reference intervals. Flags do not delete data.")
qc_cols=st.multiselect("Variables to screen",numeric,default=numeric[:min(4,len(numeric))],key="qc_cols")
rules={}
for col in qc_cols:
    with st.expander(f"QC limits: {col}"):
        a,b=st.columns(2)
        with a: lo=st.number_input(f"Minimum for {col}",value=float(pd.to_numeric(df[col],errors="coerce").min()) if df[col].notna().any() else 0.0,key=f"qcmin_{col}")
        with b: hi=st.number_input(f"Maximum for {col}",value=float(pd.to_numeric(df[col],errors="coerce").max()) if df[col].notna().any() else 1.0,key=f"qcmax_{col}")
        source=st.text_input(f"Threshold rationale for {col}",value="Study protocol / instrument specification",key=f"qcsrc_{col}")
        if lo>hi: st.error("Minimum must not exceed maximum.")
        else: rules[col]={"min":lo,"max":hi,"source":source}
if st.button("Evaluate QC rules",key="run_qc"):
    st.session_state["qc_results"]=configurable_qc(df,rules)
if "qc_results" in st.session_state: st.dataframe(st.session_state["qc_results"],use_container_width=True,hide_index=True)
