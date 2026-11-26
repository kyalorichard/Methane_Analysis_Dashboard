import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components
from platform_core.auth import require_principal
from platform_core.run_registry import list_runs, load_run_artifact
from platform_core import storage
from analysis_engine.run_artifacts import read_run_artifact
from analysis_engine.ui import header, render_sidebar_navigation, empty_state

st.set_page_config(page_title="Analysis run history | Methane Phenotype Analytics", page_icon="🗂️", layout="wide")
principal = require_principal()
render_sidebar_navigation()
header("Analysis run history", "Reopen saved analysis outputs, inspect provenance and restore the exact analysis input dataset.", badge="REPRODUCIBILITY")
active_project_id = st.session_state.get("active_project_id")
if not active_project_id:
    st.warning("Open a research project to inspect project-scoped analysis history and result artifacts.")
    st.page_link("pages/00_Project_Workspace.py", label="Open Research Workspace", icon="🗂️")
    st.stop()
try:
    runs = list_runs(250, tenant_id=principal.tenant_id, project_id=st.session_state.get("active_project_id"), user_subject=principal.subject)
    project_names = {p["id"]: p["name"] for p in storage.list_projects(principal.tenant_id, principal.subject)}
except Exception as exc:
    st.error(f"Could not open your project analysis history: {exc}")
    st.stop()
if not runs:
    empty_state("No saved analysis runs", "Complete an Integrated Analysis Centre run inside this project. Full outputs will then be retained as a reusable project artifact.")
    st.stop()

rows = []
for run in runs:
    rows.append({"Run ID": run["run_id"], "Created (UTC)": run["created_utc"],
        "Project": project_names.get(run.get("project_id"), "Project"), "Dataset": run["dataset_name"],
        "Outcome": run["outcome"], "Species": run["species"], "Status": run["status"],
        "Reusable outputs": "Available" if run.get("artifact_available") else "Metadata only",
        "Fingerprint": (run["dataset_fingerprint"] or "")[:16]})
st.metric("Saved runs", len(rows))
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

labels = {f"{r['created_utc']} · {r['dataset_name'] or 'Dataset'} · {r['run_id'][:8]}": r for r in runs}
choice = st.selectbox("Select an analysis run", list(labels))
selected = labels[choice]
left, right = st.columns(2)
with left:
    st.subheader("Run manifest")
    st.json(json.loads(selected["manifest_json"]))
with right:
    st.subheader("Recorded summary")
    st.json(json.loads(selected["summary_json"]))

if not selected.get("artifact_available"):
    st.info("This run predates Phase 2 artifact persistence or its output archive was not saved. Its metadata and summary are available, but full result tables and figures cannot be reconstructed from metadata alone.")
else:
    if st.button("Reopen full analysis outputs", type="primary", use_container_width=True):
        try:
            payload = load_run_artifact(selected["run_id"], tenant_id=principal.tenant_id,
                project_id=active_project_id, user_subject=principal.subject)
            opened = read_run_artifact(payload)
            if opened["artifact_manifest"].get("run_id") not in (None, selected["run_id"]):
                raise ValueError("Artifact run identifier does not match the selected history record.")
            st.session_state["opened_analysis_artifact"] = opened
            st.session_state["opened_analysis_run_id"] = selected["run_id"]
            st.success("Saved analysis outputs reopened and verified.")
        except Exception as exc:
            st.error(f"Could not reopen this analysis artifact: {exc}")

opened = st.session_state.get("opened_analysis_artifact")
if opened and st.session_state.get("opened_analysis_run_id") == selected["run_id"]:
    st.divider()
    st.subheader("Reopened analysis results")
    summary = opened["summary"]
    st.caption(f"Run {selected['run_id']} · {len(opened['tables'])} saved result tables")
    if opened.get("dataset") is not None:
        data = opened["dataset"]
        st.write(f"**Archived analysis input:** {len(data):,} rows × {len(data.columns):,} columns")
        if st.button("Restore archived input dataset to this session"):
            st.session_state["data"] = data
            st.session_state["data_name"] = opened["manifest"].get("dataset_name", "restored_analysis_dataset")
            st.session_state["species"] = opened["manifest"].get("species", "other")
            st.session_state["roles"] = opened["manifest"].get("roles", {})
            st.session_state["measurement_protocol"] = opened["manifest"].get("measurement_protocol", {})
            st.session_state["active_dataset_id"] = opened["manifest"].get("dataset_id")
            st.success("Archived input dataset restored to the current session. The source project dataset was not modified.")
    tabs = st.tabs(["Data quality", "Descriptive", "Group analysis", "Repeatability", "Associations", "ML benchmark", "Manifest"])
    table_map = {
        "Data quality": ["quality_control", "data_dictionary"],
        "Descriptive": ["descriptive_statistics"],
        "Group analysis": ["group_profile"],
        "Repeatability": ["session_summary", "paired_session_data"],
        "Associations": ["associations"],
        "ML benchmark": ["ml_benchmark"],
    }
    for tab, (label, names) in zip(tabs[:-1], table_map.items()):
        with tab:
            shown = False
            for name in names:
                frame = opened["tables"].get(name)
                if frame is not None:
                    st.markdown(f"**{name.replace('_', ' ').title()}**")
                    st.dataframe(frame, use_container_width=True, hide_index=True)
                    shown = True
            if not shown:
                st.info("No output table was produced for this component in the selected run.")
    with tabs[-1]:
        st.json(opened["manifest"])
        st.json(summary.get("scientific_caveats", []))
    if opened.get("figure_html"):
        st.subheader("Saved phenotype distribution figure")
        components.html(opened["figure_html"], height=520, scrolling=True)
    st.download_button("Download saved run artifact (ZIP)", payload,
        file_name=f"analysis_run_{selected['run_id']}.zip", mime="application/zip", use_container_width=True)
    if st.button("Restore input and configuration for a new run", use_container_width=True):
        if opened.get("dataset") is None:
            st.error("This artifact does not contain an input dataset snapshot, so a reproducible rerun cannot be prepared.")
        else:
            st.session_state["data"] = opened["dataset"]
            st.session_state["data_name"] = opened["manifest"].get("dataset_name", "restored_analysis_dataset")
            st.session_state["species"] = opened["manifest"].get("species", "other")
            st.session_state["roles"] = opened["manifest"].get("roles", {})
            st.session_state["measurement_protocol"] = opened["manifest"].get("measurement_protocol", {})
            st.session_state["active_dataset_id"] = opened["manifest"].get("dataset_id")
            st.session_state["integrated_analysis_restore_config"] = opened["manifest"]
            st.switch_page("pages/23_Integrated_Analysis_Centre.py")

st.caption("Phase 2 artifacts retain the exact analysis input snapshot, result tables, saved figure, run configuration and provenance. They use JSON, CSV and Parquet/HTML formats; no executable pickle files or fitted model binaries are loaded.")
