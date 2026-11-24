import streamlit as st
import pandas as pd
from platform_core.auth import require_principal
from platform_core.run_registry import list_runs
from analysis_engine.ui import header, render_sidebar_navigation, empty_state

st.set_page_config(page_title="Analysis run history | Methane Phenotype Analytics",page_icon="🗂️",layout="wide")
require_principal(); render_sidebar_navigation()
header("Analysis run history","Persistent local registry of analysis metadata and summaries. Raw datasets are not stored in this registry.",badge="AUDIT TRAIL")
try: runs=list_runs(250)
except Exception as exc: st.error(f"Could not open the local run registry: {exc}"); st.stop()
if not runs: empty_state("No saved analysis runs","Complete an Integrated Analysis Centre run to populate the registry."); st.stop()
rows=[]
for r in runs:
    rows.append({"Run ID":r["run_id"],"Created (UTC)":r["created_utc"],"Dataset":r["dataset_name"],"Outcome":r["outcome"],"Species":r["species"],"Status":r["status"],"Fingerprint":(r["dataset_fingerprint"] or "")[:16]})
st.metric("Saved runs",len(rows)); st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
choice=st.selectbox("Inspect run",[r["run_id"] for r in runs])
selected=next(r for r in runs if r["run_id"]==choice)
c1,c2=st.columns(2)
with c1: st.subheader("Manifest"); st.json(selected["manifest_json"])
with c2: st.subheader("Summary"); st.json(selected["summary_json"])
st.info("The registry stores run configuration, dataset fingerprint and summary metadata only. It does not archive source data, fitted models or full result tables.")
