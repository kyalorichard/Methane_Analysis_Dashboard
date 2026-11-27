import streamlit as st
import pandas as pd
from analysis_engine.ui import header, render_sidebar_navigation, empty_state
from analysis_engine.service_registry import get_service
build_publication_bundle = get_service("publication_bundle")
publication_tables = get_service("publication_tables")
build_scientific_report = get_service("scientific_report")
from platform_core.auth import require_principal

st.set_page_config(page_title="Publication suite | Methane Phenotype Analytics",page_icon="📚",layout="wide")
require_principal()
render_sidebar_navigation()
header("Scientific publication & reporting suite","Generate manuscript-oriented descriptive tables, interactive figures, methods notes and reproducibility metadata.",badge="V14")
from analysis_engine.ui import render_workflow_shortcuts
render_workflow_shortcuts("Reporting workflows", [
    ("Quick data & manifest exports", "pages/15_Reports_Exports.py", "📄"),
])
st.divider()
df=st.session_state.get("data")
if df is None:
    empty_state("No active dataset","Load a dataset in Project Workspace.")
    st.stop()
cols=df.columns.tolist()
numeric=df.select_dtypes(include="number").columns.tolist()
if not numeric:
    st.error("The active dataset has no numeric variables.")
    st.stop()
roles=st.session_state.get("roles",{})
default_outcome=roles.get("outcome") if roles.get("outcome") in numeric else numeric[0]
default_animal=roles.get("animal_id") if roles.get("animal_id") in cols else None
st.subheader("Report configuration")
a,b,c=st.columns(3)
with a:
    title=st.text_input("Study title",value="Methane phenotype characterisation")
    dataset_name=st.text_input("Dataset name",value=st.session_state.get("dataset_name","active_dataset"))
with b:
    species=st.text_input("Species",value=st.session_state.get("species","Not specified"))
    outcome=st.selectbox("Primary phenotype / outcome",numeric,index=numeric.index(default_outcome))
with c:
    animal=st.selectbox("Animal identifier",["— Not specified —"]+cols,index=(cols.index(default_animal)+1 if default_animal else 0))
    group=st.selectbox("Optional grouping variable",["— None —"]+cols)
animal=None if animal.startswith("—") else animal
group=None if group.startswith("—") else group
covars=st.multiselect("Numeric covariates for exploratory Spearman associations",[x for x in numeric if x!=outcome],default=[])
notes=st.text_area("Protocol and measurement notes",placeholder="Describe instrument, calibration, recording duration, phenotype units, inclusion criteria and validated QC thresholds.")
try:
    tables=publication_tables(df,outcome,animal,group,covars)
    st.markdown("### Preview")
    m1,m2,m3=st.columns(3)
    m1.metric("Source records",f"{len(df):,}")
    m2.metric("Valid outcome records",f"{pd.to_numeric(df[outcome],errors='coerce').notna().sum():,}")
    m3.metric("Analysis units",f"{tables['analysis_n']:,}")
    st.caption(f"Independent-unit summary: {tables['analysis_unit']}")
    st.dataframe(tables["outcome_summary"],use_container_width=True,hide_index=True)
    if not tables["group_summary"].empty:
        st.markdown("**Group summary**")
        st.dataframe(tables["group_summary"],use_container_width=True,hide_index=True)
    if not tables["spearman_correlations"].empty:
        st.markdown("**Exploratory Spearman correlations**")
        st.dataframe(tables["spearman_correlations"],use_container_width=True,hide_index=True)
except Exception as exc:
    st.error(f"Report preview failed: {exc}")
    st.stop()
if st.button("Generate publication and reproducibility bundle",type="primary"):
    try:
        bundle=build_publication_bundle(df,outcome=outcome,animal_id=animal,group_col=group,covariates=covars,
            dataset_name=dataset_name,study_title=title,study_species=species,protocol_notes=notes)
        st.session_state["publication_bundle"]=bundle
        st.success("Publication bundle generated.")
    except Exception as exc:
        st.error(f"Bundle generation failed: {exc}")
if "publication_bundle" in st.session_state:
    st.download_button("Download publication bundle (ZIP)",data=st.session_state["publication_bundle"],
        file_name="methane_phenotype_publication_bundle.zip",mime="application/zip")

st.divider()
st.subheader("Publication-ready report documents")
st.caption("Generate editable Word and PDF reports with descriptive tables, an outcome-distribution figure, methods, metadata and explicit interpretation limitations. These documents do not invent inferential results or replace investigator review.")
if st.button("Generate Word, PDF and complete report archive", type="primary", key="generate_scientific_documents"):
    try:
        report = build_scientific_report(df, outcome=outcome, animal_id=animal, group_col=group,
            covariates=covars, study_title=title, dataset_name=dataset_name,
            species=species, protocol_notes=notes)
        st.session_state["scientific_report_documents"] = report
        st.success("Word and PDF reports generated.")
    except Exception as exc:
        st.error(f"Scientific report generation failed: {exc}")
if "scientific_report_documents" in st.session_state:
    report = st.session_state["scientific_report_documents"]
    d1, d2, d3 = st.columns(3)
    d1.download_button("Download editable Word report", data=report["docx"],
        file_name="methane_scientific_report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    d2.download_button("Download PDF report", data=report["pdf"],
        file_name="methane_scientific_report.pdf", mime="application/pdf")
    d3.download_button("Download complete report archive", data=report["zip"],
        file_name="methane_scientific_report_complete.zip", mime="application/zip")
    st.caption(f"Report generated from {report['manifest']['source_rows']:,} source records; dataset fingerprint: {report['manifest']['dataset_fingerprint_sha256'][:16]}…")
st.info("Before manuscript submission, add protocol-specific calibration, units, sampling design, inclusion criteria, and model diagnostics. The report does not automatically claim inferential significance or causal effects.")
