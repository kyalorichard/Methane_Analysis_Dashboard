"""Tenant-scoped project lifecycle, datasets and portable project archives."""
import json
import pandas as pd
import streamlit as st
from analysis_engine.ui import header, metric_row, render_sidebar_navigation
from platform_core.auth import require_principal
from platform_core import storage as store
from platform_core.project_archive import (
    build_project_archive, inspect_project_archive, import_project_archive,
)
from platform_core.species import PROFILES
from platform_core.data_governance import inspect_dataset

render_sidebar_navigation()
principal = require_principal()
# All workspace operations use one backend-selection facade.
try:
    _backend = store.backend_name()
except Exception as exc:
    st.error(f"Storage configuration error: {exc}")
    st.stop()

list_projects = store.list_projects
create_project = store.create_project
save_dataset = store.save_dataset
list_datasets = store.list_datasets
load_dataset = store.load_dataset
get_project = store.get_project
duplicate_project = store.duplicate_project
create_project_version = store.create_project_version
list_project_versions = store.list_project_versions

header("Project workspace", "Create, import, manage, version and resume tenant-scoped livestock research projects.", badge="PROJECT LIFECYCLE")

st.caption(f"Storage backend: {'Local SQLite + filesystem' if _backend == 'local' else 'PostgreSQL + S3'}")

try:
    projects = list_projects(principal.tenant_id, principal.subject)
except Exception as exc:
    st.error(f"Unable to load projects: {exc}")
    st.stop()

# Project lifecycle entry points: reopen persisted projects, create new work, or import an archive.
open_tab, create_tab, import_tab = st.tabs(["Open existing project", "Create new project", "Import project archive"])
with open_tab:
    st.subheader("Open a saved research project")
    st.write("Reopen a project stored in your workspace. Its datasets and saved dataset-level protocol and variable mappings remain available across browser sessions. Select a dataset to restore it into the active analysis session.")
    if not projects:
        st.info("No saved projects are available yet. Create a project or import an archive to get started.")
    else:
        project_options = {f"{p['name']} · {p['species'].title()} · {p['id'][:8]}": p for p in projects}
        preferred_open = st.session_state.get("last_opened_project_id") or st.session_state.get("last_imported_project_id") or st.session_state.get("active_project_id")
        open_labels = list(project_options)
        open_default = next((label for label, item in project_options.items() if item["id"] == preferred_open), open_labels[0])
        open_label = st.selectbox("Choose a saved project", open_labels, index=open_labels.index(open_default), key="open_existing_project_choice")
        open_project = project_options[open_label]
        try:
            open_datasets = list_datasets(principal.tenant_id, open_project["id"], principal.subject)
        except Exception as exc:
            open_datasets = []
            st.error(f"Could not retrieve datasets for this project: {exc}")
        info1, info2, info3 = st.columns(3)
        info1.metric("Species", open_project["species"].title())
        info2.metric("Stored datasets", len(open_datasets))
        info3.metric("Created", str(open_project.get("created_at", "Not recorded"))[:10])
        st.caption(open_project.get("description") or "No project description has been provided.")
        dataset_choices = {"Open project without loading a dataset": None}
        dataset_choices.update({f"{d['name']} · {int(d.get('row_count') or 0):,} rows · {str(d.get('created_at', ''))[:10]}": d for d in open_datasets})
        chosen_dataset_label = st.selectbox("Dataset to restore (optional)", list(dataset_choices), key="open_project_dataset_choice")
        if st.button("Open project", type="primary", key="open_saved_project_action"):
            previous_project_id = st.session_state.get("active_project_id")
            if previous_project_id and previous_project_id != open_project["id"]:
                for state_key in ("data", "raw_data_snapshot", "data_name", "roles", "dataset_profile", "active_dataset_id", "active_dataset_key", "forecast_series", "forecast_results", "ml_benchmark_results", "nested_ml_results", "cluster_metrics", "cluster_labels"):
                    st.session_state.pop(state_key, None)
                st.session_state.pop("analysis_settings_scope_key", None)
            st.session_state["active_project_id"] = open_project["id"]
            st.session_state["active_project_species"] = open_project["species"]
            st.session_state["species"] = open_project["species"]
            st.session_state["analysis_project_scope"] = open_project["id"]
            st.session_state["analysis_project_legacy_scope"] = open_project["name"]
            st.session_state["analysis_species_scope"] = open_project["species"].lower()
            st.session_state["last_opened_project_id"] = open_project["id"]
            recent_ids = [open_project["id"]] + [x for x in st.session_state.get("recent_project_ids", []) if x != open_project["id"]]
            st.session_state["recent_project_ids"] = recent_ids[:8]
            st.session_state["workspace_active_project"] = open_label
            chosen_dataset = dataset_choices[chosen_dataset_label]
            if chosen_dataset is not None:
                try:
                    restored_df, restored_name, restored_species = load_dataset(principal.tenant_id, open_project["id"], chosen_dataset["id"], principal.subject)
                    saved_config = store.get_dataset_configuration(principal.tenant_id, principal.subject, open_project["id"], chosen_dataset["id"])
                    from platform_core.species import infer_species_roles
                    restored_protocol = saved_config.get("measurement_protocol") or {}
                    st.session_state["data"] = restored_df
                    st.session_state["raw_data_snapshot"] = restored_df.copy(deep=True)
                    st.session_state["cleaning_log"] = []
                    st.session_state["data_name"] = restored_name
                    st.session_state["active_dataset_id"] = chosen_dataset["id"]
                    st.session_state["species"] = saved_config.get("species") or restored_species
                    st.session_state["roles"] = saved_config.get("variable_mapping") or infer_species_roles(restored_df.columns, restored_species)
                    st.session_state["measurement_protocol"] = restored_protocol
                    st.session_state["protocol_instrument"] = restored_protocol.get("instrument", "")
                    st.session_state["protocol_method"] = restored_protocol.get("method", "Not specified")
                    st.session_state["protocol_units"] = restored_protocol.get("units", "")
                    st.session_state["protocol_calibration"] = restored_protocol.get("calibration_status", "Not documented")
                    st.session_state["protocol_ref"] = restored_protocol.get("protocol_reference", "")
                    st.session_state["protocol_min_duration"] = restored_protocol.get("minimum_recording_duration_seconds", 0.0)
                except Exception as exc:
                    st.error(f"Project opened, but the selected dataset could not be restored: {exc}")
                    st.stop()
            else:
                for state_key in ("data", "raw_data_snapshot", "data_name", "roles", "dataset_profile", "active_dataset_id", "active_dataset_key", "cleaning_log", "measurement_protocol", "protocol_instrument", "protocol_method", "protocol_units", "protocol_calibration", "protocol_ref", "protocol_min_duration"):
                    st.session_state.pop(state_key, None)
            st.success(f"Opened project: {open_project['name']}")
            st.rerun()
        recent_ids = st.session_state.get("recent_project_ids", [])
        recent_projects = [p for pid in recent_ids for p in projects if p["id"] == pid]
        if recent_projects:
            st.divider()
            st.caption("Recently opened in this browser session")
            st.dataframe(pd.DataFrame([{"Project": p["name"], "Species": p["species"].title(), "Created": p.get("created_at")} for p in recent_projects]), use_container_width=True, hide_index=True)

with create_tab:
    with st.form("create_project_form", clear_on_submit=True):
        st.subheader("Create a research project")
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Project name", placeholder="e.g. ICARDA Sheep Methane Phenotyping")
            species_label = st.selectbox("Primary livestock species", [p.label for p in PROFILES.values()])
        with c2:
            description = st.text_area("Study objective / description", height=105)
        create_submit = st.form_submit_button("Create project", type="primary")
    if create_submit:
        if not new_name.strip():
            st.error("Enter a project name.")
        else:
            try:
                species = next(p.key for p in PROFILES.values() if p.label == species_label)
                pid = create_project(principal.tenant_id, principal.subject, new_name.strip(), species, description.strip())
                st.session_state["last_opened_project_id"] = pid
                st.session_state["active_project_id"] = pid
                st.session_state["active_project_species"] = species
                st.session_state["analysis_project_scope"] = pid
                st.success(f"Project created successfully (ID: {pid}). It is now selected as your active project.")
                st.rerun()
            except Exception as exc:
                st.error(f"Project creation failed: {exc}")

with import_tab:
    st.subheader("Import a complete project archive")
    st.write("Restore a project exported from this platform. The archive contains project metadata, datasets in canonical Parquet format, measurement protocols, and available user/project-scoped analysis settings and experiment records.")
    archive_file = st.file_uploader("Select project ZIP archive", type=["zip"], key="project_archive_upload", help="Maximum archive size: 200 MB. The archive is validated before any project is created.")
    if archive_file is not None:
        archive_bytes = archive_file.getvalue()
        try:
            preview = inspect_project_archive(archive_bytes)
            source_project = preview["project"]
            st.success("Archive structure and dataset SHA-256 checks passed.")
            a, b, c = st.columns(3)
            a.metric("Source project", source_project["name"])
            b.metric("Species", source_project["species"].title())
            c.metric("Datasets", len(preview["datasets"]))
            st.dataframe(pd.DataFrame([{"Dataset": d.get("original_filename"), "Species": d.get("species"), "Rows": d.get("row_count"), "Columns": d.get("column_count")} for d in preview["datasets"]]), use_container_width=True, hide_index=True)
            destination_name = st.text_input("Name for imported project", value=source_project["name"], key="import_project_name")
            restore_state = st.checkbox("Restore included analysis settings and experiment metadata", value=True, help="Restores metadata under your account and the imported project name. It does not recreate fitted model binaries or historical result files.")
            confirm_import = st.checkbox("I understand this creates a new project and does not overwrite an existing project.", key="confirm_project_import")
            if st.button("Import project", type="primary", disabled=not (destination_name.strip() and confirm_import), key="execute_project_import"):
                with st.spinner("Importing project metadata and datasets into tenant storage..."):
                    result = import_project_archive(archive_bytes, principal.tenant_id, principal.subject, destination_name, restore_state)
                st.success(f"Imported '{result['project_name']}' with {result['datasets_imported']} dataset(s). New project ID: {result['project_id']}")
                st.session_state["last_imported_project_id"] = result["project_id"]
                st.session_state["last_opened_project_id"] = result["project_id"]
                st.session_state["active_project_id"] = result["project_id"]
                st.rerun()
        except Exception as exc:
            st.error(f"Archive validation failed: {exc}")

st.divider()
if not projects:
    st.info("No projects are currently available to your account. Create a new project or import an existing project archive above.")
    st.stop()

project_labels = {f"{p['name']} · {p['species'].title()} · {p['id'][:8]}": p for p in projects}
preferred = st.session_state.get("last_opened_project_id") or st.session_state.get("last_imported_project_id") or st.session_state.get("active_project_id")
default_label = next((label for label, item in project_labels.items() if item["id"] == preferred), next(iter(project_labels)))
selected_label = st.selectbox("Active project", list(project_labels), index=list(project_labels).index(default_label), key="workspace_active_project")
project = project_labels[selected_label]
project_id = project["id"]
st.session_state["active_project_id"] = project_id
st.session_state["active_project_species"] = project["species"]
st.session_state["species"] = project["species"]
st.session_state["analysis_project_scope"] = project_id
st.session_state["analysis_project_legacy_scope"] = project["name"]

try:
    datasets = list_datasets(principal.tenant_id, project_id, principal.subject)
except Exception as exc:
    st.error(f"Unable to retrieve project datasets: {exc}")
    datasets = []

metric_row([
    ("SPECIES", project["species"].upper(), "Primary project species"),
    ("DATASETS", f"{len(datasets):,}", "Persisted datasets"),
    ("RECORDS", f"{sum(int(d.get('row_count') or 0) for d in datasets):,}", "Across stored datasets"),
])

manage_tab, data_tab, lifecycle_tab = st.tabs(["Project overview", "Datasets & protocols", "Versioning & portability"])
with manage_tab:
    st.subheader(project["name"])
    st.write(project.get("description") or "No study description has been provided.")
    st.caption(f"Project ID: {project_id} · Created: {project.get('created_at')} · Tenant: {principal.tenant_id}")
    st.markdown("**Resume analysis**")
    if datasets:
        options = {f"{d['name']} · {int(d.get('row_count') or 0):,} rows · {d.get('created_at')}": d for d in datasets}
        choice = st.selectbox("Choose a stored dataset", list(options), key="resume_dataset_choice")
        if st.button("Load dataset and resume analysis", type="primary", key="resume_analysis"):
            selected = options[choice]
            df, name, species = load_dataset(principal.tenant_id, project_id, selected["id"], principal.subject)
            st.session_state["data"] = df
            st.session_state["raw_data_snapshot"] = df.copy(deep=True)
            st.session_state["cleaning_log"] = []
            st.session_state["data_name"] = name
            st.session_state["species"] = species
            st.session_state["active_dataset_id"] = selected["id"]
            st.session_state["active_project_id"] = project_id
            st.session_state["analysis_project_scope"] = project_id
            st.session_state["analysis_project_legacy_scope"] = project["name"]
            from platform_core.species import infer_species_roles
            saved_config = store.get_dataset_configuration(principal.tenant_id, principal.subject, project_id, selected["id"])
            st.session_state["species"] = saved_config.get("species") or species
            st.session_state["roles"] = saved_config.get("variable_mapping") or infer_species_roles(df.columns, species)
            protocol = saved_config.get("measurement_protocol") or {}
            st.session_state["measurement_protocol"] = protocol
            st.session_state["protocol_instrument"] = protocol.get("instrument", "")
            st.session_state["protocol_method"] = protocol.get("method", "Not specified")
            st.session_state["protocol_units"] = protocol.get("units", "")
            st.session_state["protocol_calibration"] = protocol.get("calibration_status", "Not documented")
            st.session_state["protocol_ref"] = protocol.get("protocol_reference", "")
            st.session_state["protocol_min_duration"] = protocol.get("minimum_recording_duration_seconds", 0.0)
            st.success("Dataset restored with its saved species, variable mapping and measurement protocol. Open the analytical modules from the navigation menu.")
    else:
        st.info("This project has no stored datasets yet. Upload the study data in the Datasets & protocols tab.")

    with st.expander("Save project checkpoint", expanded=False):
        st.caption("Your datasets and dataset-level configurations are already persisted in project storage. Create a named checkpoint to record the current project metadata and dataset manifest before a major analysis milestone.")
        quick_checkpoint_note = st.text_input("Checkpoint description", placeholder="e.g. Baseline data preparation completed", key="quick_project_checkpoint_note")
        if st.button("Save project checkpoint", type="primary", key="quick_save_project_checkpoint"):
            try:
                version = create_project_version(principal.tenant_id, principal.subject, project_id, quick_checkpoint_note.strip())
                st.success(f"Project checkpoint v{version} saved.")
            except Exception as exc:
                st.error(f"Project checkpoint could not be saved: {exc}")

    with st.expander("Duplicate this project"):
        st.caption("Creates a separate project and copies all stored datasets and protocol metadata. The source project is not modified.")
        copy_name = st.text_input("New project name", value=f"{project['name']} — Copy", key="duplicate_project_name")
        if st.button("Create independent project copy", disabled=not copy_name.strip(), key="duplicate_project_action"):
            try:
                with st.spinner("Copying project datasets..."):
                    new_id = duplicate_project(principal.tenant_id, principal.subject, project_id, copy_name.strip())
                st.success(f"Project copy created: {new_id}")
                st.session_state["last_imported_project_id"] = new_id
                st.rerun()
            except Exception as exc:
                st.error(f"Project duplication did not complete: {exc}")

with data_tab:
    st.subheader("Upload a dataset to the active project")
    with st.expander("Measurement protocol metadata", expanded=True):
        p1, p2 = st.columns(2)
        with p1:
            instrument = st.text_input("Instrument / measurement system", key="upload_instrument")
            method = st.selectbox("Measurement method", ["Not specified", "Respiration chamber", "GreenFeed", "Laser methane detector", "Portable accumulation chamber", "Breath sampling", "Other"], key="upload_method")
            units = st.text_input("Methane variable units", key="upload_units")
        with p2:
            calibration = st.selectbox("Calibration status", ["Not documented", "Manufacturer calibration only", "Study-specific validated calibration", "Not applicable / presence-only signal"], key="upload_calibration")
            sop = st.text_input("Protocol / SOP reference", key="upload_sop")
            min_duration = st.number_input("Minimum valid recording duration (seconds)", min_value=0.0, value=0.0, step=10.0, key="upload_min_duration")
    protocol = {"instrument": instrument, "method": method, "units": units, "calibration_status": calibration, "protocol_reference": sop, "minimum_recording_duration_seconds": min_duration}
    st.session_state["measurement_protocol"] = protocol
    up = st.file_uploader("Upload dataset (CSV, Parquet or Excel)", type=["csv", "parquet", "pq", "xlsx", "xls"], key="persistent_dataset_upload", help="All newly uploaded project datasets are stored internally as Snappy-compressed Parquet.")
    if up is not None:
        try:
            raw = up.getvalue()
            from analysis_engine.io import load_uploaded_data
            df = load_uploaded_data(up)
            profile = inspect_dataset(df, project["species"])
            metric_row([("RECORDS", f"{len(df):,}", "Rows detected"), ("VARIABLES", str(df.shape[1]), "Columns detected"), ("UNIQUE ANIMALS", str(profile["n_animals"] if profile["n_animals"] is not None else "Not mapped"), "Species adapter inference")])
            st.json({"species": project["species"], "candidate_roles": profile["roles"], "missing_percent": profile["missing_percent"], "duplicate_rows": profile["duplicate_rows"]})
            if st.button("Save dataset to project storage", type="primary", key="save_project_dataset"):
                result = save_dataset(principal.tenant_id, principal.subject, project_id, up.name, raw, df, project["species"], protocol)
                st.success(f"Dataset saved in canonical Parquet format. Storage SHA-256: {result['sha256']}")
                st.rerun()
        except Exception as exc:
            st.error(f"Dataset validation/upload failed: {exc}")

    st.subheader("Stored datasets")
    if datasets:
        display = [{"Name": d["name"], "Species": d["species"], "Rows": d["row_count"], "Format": d["file_format"], "Source format": d.get("source_format"), "Original retained": bool(d.get("source_sha256")), "Created": d["created_at"], "Parquet SHA-256": d.get("sha256"), "Source SHA-256": d.get("source_sha256")} for d in datasets]
        st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)
        with st.expander("Dataset protocol, quality and source-file recovery"):
            for d in datasets:
                st.markdown(f"**{d['name']}**")
                st.json({"protocol": d.get("protocol_json") or {}, "quality_control": d.get("qc_summary") or {}, "schema": d.get("schema_json") or {}, "canonical_parquet_sha256": d.get("sha256"), "original_source_sha256": d.get("source_sha256")})
            source_options = {f"{d['name']} · {d['id'][:8]}": d for d in datasets if d.get("source_sha256")}
            if source_options:
                source_label = st.selectbox("Original source file", list(source_options), key="raw_source_download_select")
                source_item = source_options[source_label]
                try:
                    source_bytes, source_name, source_ext = store.load_raw_source(principal.tenant_id, project_id, source_item["id"], principal.subject)
                    mime = {"csv":"text/csv", "parquet":"application/vnd.apache.parquet", "pq":"application/vnd.apache.parquet", "xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xls":"application/vnd.ms-excel"}.get(source_ext, "application/octet-stream")
                    st.download_button("Download immutable original upload", source_bytes, file_name=source_name, mime=mime, key="download_original_source")
                except Exception as exc:
                    st.error(f"Original source file could not be recovered: {exc}")
            else:
                st.caption("No original source object is available for the selected legacy datasets. New uploads retain both original bytes and canonical Parquet.")

with lifecycle_tab:
    st.subheader("Project version checkpoints")
    st.write("A checkpoint records project metadata and the dataset manifest (including hashes and protocol metadata). Dataset bytes remain in encrypted object storage; this is not a full point-in-time database backup.")
    checkpoint_note = st.text_input("Checkpoint note", placeholder="e.g. Baseline dataset QC completed")
    if st.button("Create project version checkpoint", type="primary", key="create_project_checkpoint"):
        try:
            version = create_project_version(principal.tenant_id, principal.subject, project_id, checkpoint_note.strip())
            st.success(f"Project checkpoint v{version} created.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not create checkpoint: {exc}")
    try:
        versions = list_project_versions(principal.tenant_id, principal.subject, project_id)
        if versions:
            st.dataframe(pd.DataFrame([{"Version": v["version_number"], "Created": v["created_at"], "Note": (v["snapshot_json"] or {}).get("note", ""), "Datasets in snapshot": len((v["snapshot_json"] or {}).get("datasets", []))} for v in versions]), use_container_width=True, hide_index=True)
        else:
            st.caption("No version checkpoints have been created yet.")
    except Exception as exc:
        st.warning(f"Version history is unavailable: {exc}")

    st.divider()
    st.subheader("Export / backup project")
    st.write("Creates a portable ZIP with project metadata, all stored datasets as Parquet, measurement protocols, SHA-256 integrity hashes, and available user/project-scoped analysis settings and experiment metadata. Fitted model binaries, raw execution logs and historical result files are not included unless separately stored as datasets.")
    include_state = st.checkbox("Include analysis settings and experiment metadata", value=True, key="export_research_state")
    if st.button("Prepare project export", type="primary", key="prepare_project_export"):
        try:
            with st.spinner("Building portable project archive..."):
                archive = build_project_archive(principal.tenant_id, principal.subject, project_id, include_state)
            st.session_state["project_export_bytes"] = archive
            st.session_state["project_export_filename"] = f"{project['name'].strip().replace(' ', '_')}_project_export.zip"
            st.success(f"Project archive prepared ({len(archive) / (1024 * 1024):.2f} MB). Download it below and retain it as a project backup.")
        except Exception as exc:
            st.error(f"Project export failed: {exc}")
    if st.session_state.get("project_export_bytes"):
        st.download_button("Download project ZIP", st.session_state["project_export_bytes"], st.session_state.get("project_export_filename", "project_export.zip"), "application/zip", key="download_project_archive")
