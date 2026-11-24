import json
import streamlit as st
import pandas as pd
from analysis_engine.ui import header, render_sidebar_navigation, empty_state
from platform_core.auth import require_principal
from platform_core.run_registry import list_runs
from analysis_engine.research_intelligence import compare_run_manifests

st.set_page_config(page_title="Analysis comparison | Methane Phenotype Analytics", page_icon="🧾", layout="wide")
require_principal()
render_sidebar_navigation()
header("Analysis run comparison", "Compare recorded dataset fingerprints, study configuration, validation settings and outputs across completed analyses.", badge="REPRODUCIBILITY")

try:
    runs=list_runs(limit=200)
except Exception as exc:
    st.error(f"Unable to read the local analysis registry: {exc}")
    st.stop()
if len(runs)<2:
    empty_state("At least two analysis runs are required",
                "Run and save two analyses using the integrated analysis centre or another registered workflow. This page compares stored metadata; it does not reconstruct missing analysis details.")
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
c4.metric("Same outcome","Yes" if r1["outcome"]==r2["outcome"] else "No")
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
st.info("Comparison is limited to metadata persisted in the run manifests and summaries. It does not establish statistical significance of differences between runs.")
