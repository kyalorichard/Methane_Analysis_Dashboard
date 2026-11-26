import re
import streamlit as st
import pandas as pd
from analysis_engine.ui import header, metric_row, render_sidebar_navigation, empty_state
from platform_core.auth import require_principal

st.set_page_config(page_title="Data preparation studio | Methane Phenotype Analytics",page_icon="🧹",layout="wide")
require_principal()
render_sidebar_navigation()
header("Data preparation studio","Create an auditable analysis copy while preserving the source dataset. Cleaning decisions are explicit and reversible within this session.",badge="DATA GOVERNANCE")

df=st.session_state.get("data")
if df is None:
    empty_state("No active dataset","Import a dataset before starting data preparation.")
    st.stop()

if "raw_data_snapshot" not in st.session_state:
    st.session_state["raw_data_snapshot"]=df.copy(deep=True)
if "cleaning_log" not in st.session_state:
    st.session_state["cleaning_log"]=[]

raw=st.session_state["raw_data_snapshot"]
current=st.session_state["data"]
metric_row([
    ("SOURCE RECORDS",f"{len(raw):,}","Preserved session snapshot"),
    ("ACTIVE RECORDS",f"{len(current):,}","Current analysis copy"),
    ("VARIABLES",str(current.shape[1]),"Current columns"),
    ("DUPLICATE ROWS",str(current.duplicated().sum()),"Exact duplicates")
])

st.subheader("1. Inspect data quality")
quality=pd.DataFrame({
    "variable":current.columns.astype(str),
    "dtype":[str(x) for x in current.dtypes],
    "missing_n":current.isna().sum().values,
    "missing_percent":(current.isna().mean()*100).round(2).values,
    "unique_n":current.nunique(dropna=True).values
}).sort_values("missing_percent",ascending=False)
st.dataframe(quality,use_container_width=True,hide_index=True)
st.caption("Missing values are not automatically imputed. Missingness may be informative and should be handled according to the measurement protocol and analysis objective.")

st.subheader("2. Select preparation operations")
with st.container(border=True):
    drop_duplicates=st.checkbox("Remove exact duplicate rows",value=False)
    drop_empty=st.checkbox("Remove fully empty rows",value=True)
    trim_strings=st.checkbox("Trim leading/trailing whitespace in text columns",value=True)
    normalise_names=st.checkbox("Standardise column names to snake_case",value=False)
    numeric_candidates=[c for c in current.columns if current[c].dtype=="object"]
    convert_numeric=st.multiselect("Convert selected columns to numeric",numeric_candidates)
    date_candidates=[c for c in current.columns if current[c].dtype=="object"]
    convert_dates=st.multiselect("Parse selected columns as dates",date_candidates)
    st.warning("Numeric and date conversion may introduce missing values when source entries cannot be parsed. Review the preview before applying.")

preview=current.copy(deep=True)
if trim_strings:
    for c in preview.select_dtypes(include=["object","string"]).columns:
        preview[c]=preview[c].map(lambda x:x.strip() if isinstance(x,str) else x)
for c in convert_numeric:
    if c in preview.columns: preview[c]=pd.to_numeric(preview[c],errors="coerce")
for c in convert_dates:
    if c in preview.columns: preview[c]=pd.to_datetime(preview[c],errors="coerce")
if normalise_names:
    names=[re.sub(r"_+","_",re.sub(r"[^0-9a-zA-Z]+","_",str(c).strip())).strip("_").lower() for c in preview.columns]
    if len(set(names))!=len(names):
        st.error("Column-name standardisation would create duplicate names. Rename conflicting columns manually first.")
    else:
        preview.columns=names
if drop_empty: preview=preview.dropna(how="all")
if drop_duplicates: preview=preview.drop_duplicates()

metric_row([
    ("PREVIEW RECORDS",f"{len(preview):,}","After selected operations"),
    ("RECORDS REMOVED",f"{len(current)-len(preview):,}","Preview only"),
    ("PREVIEW VARIABLES",str(preview.shape[1]),"After selected operations"),
    ("NEW MISSING CELLS",f"{int(preview.isna().sum().sum()-current.isna().sum().sum()):,}","Can increase after parsing")
])
st.dataframe(preview.head(30),use_container_width=True,hide_index=True)
c1,c2=st.columns(2)
with c1:
    if st.button("Apply preparation to active analysis copy",type="primary",use_container_width=True):
        st.session_state["data"]=preview.copy()
        from analysis_engine.io import infer_roles
        from platform_core.species import infer_species_roles
        species=st.session_state.get("species","other")
        st.session_state["roles"]=infer_species_roles(preview.columns,species)
        st.session_state["cleaning_log"].append({
            "operations":{"drop_duplicates":drop_duplicates,"drop_empty_rows":drop_empty,
                          "trim_text":trim_strings,"standardise_column_names":normalise_names,
                          "convert_numeric":convert_numeric,"convert_dates":convert_dates},
            "records_before":len(current),"records_after":len(preview),
            "timestamp_utc":pd.Timestamp.utcnow().isoformat()
        })
        st.success("Prepared analysis copy updated. Source snapshot remains available in this session.")
        st.rerun()
with c2:
    if st.button("Restore source snapshot",use_container_width=True):
        st.session_state["data"]=raw.copy(deep=True)
        st.session_state["cleaning_log"]=[]
        from platform_core.species import infer_species_roles
        st.session_state["roles"]=infer_species_roles(raw.columns,st.session_state.get("species","other"))
        st.success("Restored the source snapshot.")
        st.rerun()

st.subheader("3. Preparation history")
if st.session_state["cleaning_log"]:
    st.dataframe(pd.DataFrame(st.session_state["cleaning_log"]),use_container_width=True,hide_index=True)
else:
    st.info("No preparation operations have been applied in this session.")

st.download_button("Download current prepared dataset (CSV)",current.to_csv(index=False).encode("utf-8"),
                   file_name="prepared_methane_phenotype_dataset.csv",mime="text/csv")

st.divider()
st.subheader("4. Save prepared data as a project dataset version")
project_id = st.session_state.get("active_project_id")
source_dataset_id = st.session_state.get("active_dataset_id")
if not project_id:
    st.warning("Open or create a research project before saving a durable dataset version. The current prepared data remain available in this browser session.")
else:
    st.caption("Saving creates a new immutable project dataset. The previous saved dataset is retained, and the preparation log is attached to the new version's metadata.")
    if st.button("Save prepared dataset version", type="primary", use_container_width=True,
                 disabled=current is None or current.empty):
        try:
            from pathlib import Path
            from datetime import datetime, timezone
            from analysis_engine.io import dataframe_to_parquet_bytes
            from platform_core import storage as store
            from platform_core.auth import require_principal
            principal = require_principal()
            source_name = st.session_state.get("data_name", "methane_dataset")
            stem = Path(source_name).stem or "methane_dataset"
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            version_name = f"{stem}_prepared_{timestamp}.parquet"
            parquet_bytes = dataframe_to_parquet_bytes(current, compression="snappy")
            species = st.session_state.get("species", "other")
            protocol = st.session_state.get("measurement_protocol", {}) or {}
            preparation = {
                "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_dataset_id": source_dataset_id,
                "source_dataset_name": source_name,
                "operations": st.session_state.get("cleaning_log", []),
                "records_before": len(raw),
                "records_after": len(current),
                "columns_before": list(map(str, raw.columns)),
                "columns_after": list(map(str, current.columns)),
            }
            saved = store.save_dataset(
                principal.tenant_id, principal.subject, project_id,
                version_name, parquet_bytes, current, species,
                {"preparation": preparation, "measurement_protocol": protocol,
                 "variable_mapping": st.session_state.get("roles", {})},
            )
            store.save_dataset_configuration(
                principal.tenant_id, principal.subject, project_id, saved["id"],
                species, st.session_state.get("roles", {}), protocol,
            )
            st.session_state["active_dataset_id"] = saved["id"]
            st.session_state["active_dataset_name"] = version_name
            st.session_state["data_name"] = version_name
            st.session_state["raw_data_snapshot"] = current.copy(deep=True)
            st.session_state["cleaning_log"] = []
            st.session_state["prepared_dataset_saved"] = version_name
            st.success(f"Saved {version_name} to the active research project. The new version is now the active dataset.")
            st.rerun()
        except Exception as exc:
            st.error(f"Prepared dataset could not be saved: {exc}")
