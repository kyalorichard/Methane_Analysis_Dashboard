import json
import streamlit as st
import pandas as pd
from analysis_engine.ui import header, render_sidebar_navigation, empty_state
from platform_core.auth import require_principal
from platform_core.run_registry import list_runs, load_run_artifact
from analysis_engine.run_artifacts import read_run_artifact
from analysis_engine.research_intelligence import compare_run_manifests

st.set_page_config(page_title="Analysis comparison | Methane Phenotype Analytics", page_icon="🧾", layout="wide")
principal = require_principal()
render_sidebar_navigation()
header("Analysis run comparison", "Compare recorded dataset fingerprints, study configuration, validation settings and outputs across completed analyses.", badge="REPRODUCIBILITY")

try:
    runs=list_runs(limit=200, tenant_id=principal.tenant_id, project_id=st.session_state.get("active_project_id"), user_subject=principal.subject)
except Exception as exc:
    st.error(f"Unable to read your project analysis history: {exc}")
    st.stop()
if len(runs)<2:
    empty_state("At least two analysis runs are required",
                "Open a research project and save at least two analyses. This page compares stored metadata; it does not reconstruct missing result artifacts.")
    st.stop()

labels={f"{r['created_utc']} · {r['dataset_name'] or 'Dataset'} · {r['run_id'][:8]}":r for r in runs}
opts=list(labels)
a,b=st.columns(2)
left=a.selectbox("First analysis run",opts,index=0)
right=b.selectbox("Second analysis run",opts,index=1)
r1,r2=labels[left],labels[right]
m1=json.loads(r1["manifest_json"]);m2=json.loads(r2["manifest_json"])
summary1=json.loads(r1["summary_json"]);summary2=json.loads(r2["summary_json"])
c1,c2,c3,c4=st.columns(4)
c1.metric("Run 1 status",r1["status"])
c2.metric("Run 2 status",r2["status"])
c3.metric("Same dataset fingerprint","Yes" if r1["dataset_fingerprint"]==r2["dataset_fingerprint"] else "No")
c4.metric("Both full artifacts available", "Yes" if r1.get("artifact_available") and r2.get("artifact_available") else "No")
diff=compare_run_manifests(m1,m2)
changed=diff[diff["changed"]]
st.subheader("Configuration and provenance differences")
st.metric("Changed metadata fields",f"{len(changed):,}")
st.dataframe(changed,use_container_width=True,hide_index=True)
with st.expander("All compared metadata fields"):
    st.dataframe(diff,use_container_width=True,hide_index=True)
st.subheader("Recorded analysis summaries")
x,y=st.columns(2)
with x:
    st.markdown("**Run 1**")
    st.json(summary1)
with y:
    st.markdown("**Run 2**")
    st.json(summary2)
st.divider()
st.subheader("Compare saved result tables")
if r1.get("artifact_available") and r2.get("artifact_available"):
    if st.button("Load both full result artifacts", type="primary"):
        try:
            a1 = read_run_artifact(load_run_artifact(r1["run_id"], tenant_id=principal.tenant_id,
                project_id=st.session_state.get("active_project_id"), user_subject=principal.subject))
            a2 = read_run_artifact(load_run_artifact(r2["run_id"], tenant_id=principal.tenant_id,
                project_id=st.session_state.get("active_project_id"), user_subject=principal.subject))
            st.session_state["comparison_artifacts"] = {"run_ids": [r1["run_id"], r2["run_id"]], "left": a1, "right": a2}
        except Exception as exc:
            st.error(f"Could not load the saved result artifacts: {exc}")
    loaded = st.session_state.get("comparison_artifacts")
    if loaded and loaded.get("run_ids") == [r1["run_id"], r2["run_id"]]:
        common = sorted(set(loaded["left"]["tables"]) & set(loaded["right"]["tables"]))
        if common:
            table_name = st.selectbox("Result table", common)
            left_table = loaded["left"]["tables"][table_name]
            right_table = loaded["right"]["tables"][table_name]
            lcol, rcol = st.columns(2)
            with lcol:
                st.markdown("**Run 1**")
                st.dataframe(left_table, use_container_width=True, hide_index=True)
            with rcol:
                st.markdown("**Run 2**")
                st.dataframe(right_table, use_container_width=True, hide_index=True)
            if list(left_table.columns) == list(right_table.columns) and left_table.shape == right_table.shape:
                numeric_cols = [c for c in left_table.select_dtypes(include="number").columns if c in right_table.columns]
                if numeric_cols:
                    st.caption("Cell-wise numeric differences (Run 2 − Run 1); row alignment follows the saved table order.")
                    delta = right_table[numeric_cols].reset_index(drop=True) - left_table[numeric_cols].reset_index(drop=True)
                    st.dataframe(delta, use_container_width=True, hide_index=True)
        else:
            st.info("The selected runs do not share any saved result-table names.")
else:
    st.info("Full output comparison is available when both runs have persisted result artifacts. Older metadata-only runs remain comparable by configuration and summary.")
st.warning("Table differences are descriptive comparisons, not hypothesis tests. They do not establish statistical significance or causal effects.")
