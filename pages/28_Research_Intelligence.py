import json
import streamlit as st
import pandas as pd
import plotly.express as px
from analysis_engine.ui import header, metric_row, render_sidebar_navigation, empty_state
from analysis_engine.research_intelligence import (
    dataset_readiness, automated_recommendations, flag_data_quality,
    calibration_diagnostics, phenotype_evidence_matrix
)
from platform_core.auth import require_principal

st.set_page_config(page_title="Research intelligence | Methane Phenotype Analytics", page_icon="🧭", layout="wide")
require_principal()
render_sidebar_navigation()
header("Research intelligence", "Integrated dataset readiness, measurement QC, calibration, phenotype evidence and analysis recommendations.", badge="RESEARCH INTELLIGENCE")

df = st.session_state.get("data")
if df is None:
    empty_state("No active dataset", "Import a dataset from the sidebar or load the example sheep dataset to activate research intelligence.")
    st.stop()

roles = st.session_state.get("roles", {})
protocol = st.session_state.get("measurement_protocol", {})
animal = roles.get("animal_id") if roles.get("animal_id") in df.columns else None
outcome = roles.get("methane") if roles.get("methane") in df.columns else None
duration = roles.get("recording_duration") if roles.get("recording_duration") in df.columns else None
readiness = dataset_readiness(df, roles, protocol)

metric_row([
    ("READINESS", f"{readiness['readiness_pct']:.0f}%", "Metadata and data structure checks; not a scientific certification"),
    ("RECORDS", f"{len(df):,}", "Source observations"),
    ("ANIMALS", f"{df[animal].nunique():,}" if animal else "Not mapped", "Unique animal identifiers"),
    ("MISSING CELLS", f"{readiness['missing_pct']:.1f}%", "Percentage of all cells missing"),
])

tabs = st.tabs(["Study setup & readiness", "Automated QC", "Calibration & agreement", "Phenotype evidence", "Analysis recommendations"])

with tabs[0]:
    st.subheader("Study and measurement protocol")
    with st.form("measurement_protocol_form"):
        a,b,c = st.columns(3)
        with a:
            instrument = st.text_input("Instrument / measurement system", value=protocol.get("instrument",""))
            method = st.selectbox("Measurement method",
                ["Not specified","Respiration chamber","GreenFeed","Laser methane detector",
                 "Portable accumulation chamber","Breath sampling","Other"],
                index=["Not specified","Respiration chamber","GreenFeed","Laser methane detector","Portable accumulation chamber","Breath sampling","Other"].index(protocol.get("method","Not specified")) if protocol.get("method","Not specified") in ["Not specified","Respiration chamber","GreenFeed","Laser methane detector","Portable accumulation chamber","Breath sampling","Other"] else 0)
        with b:
            units = st.text_input("Methane signal / phenotype units", value=protocol.get("units",""))
            calibration = st.selectbox("Calibration status",
                ["Not documented","Manufacturer calibration only","Study-specific validated calibration","Not applicable / signal proxy"],
                index=["Not documented","Manufacturer calibration only","Study-specific validated calibration","Not applicable / signal proxy"].index(protocol.get("calibration_status","Not documented")) if protocol.get("calibration_status","Not documented") in ["Not documented","Manufacturer calibration only","Study-specific validated calibration","Not applicable / signal proxy"] else 0)
        with c:
            sampling = st.text_input("Sampling frequency", value=protocol.get("sampling_frequency",""))
            sop = st.text_input("Protocol / SOP reference", value=protocol.get("protocol_reference",""))
        min_duration = st.number_input("Minimum valid recording duration (seconds)", min_value=0.0,
            value=float(protocol.get("minimum_recording_duration_seconds",0) or 0), step=10.0)
        reference = st.text_input("Calibration reference / validation dataset", value=protocol.get("reference_method",""))
        submitted = st.form_submit_button("Save study protocol", type="primary")
    if submitted:
        st.session_state["measurement_protocol"] = {
            "instrument":instrument.strip(),"method":method,"units":units.strip(),
            "calibration_status":calibration,"sampling_frequency":sampling.strip(),
            "protocol_reference":sop.strip(),"minimum_recording_duration_seconds":min_duration,
            "reference_method":reference.strip()
        }
        st.success("Protocol metadata saved to this research session.")
        st.rerun()

    st.subheader("Dataset readiness checklist")
    for label, ok, detail in readiness["checks"]:
        st.write(("✅" if ok else "⚠️") + f" **{label}** — {detail}")
    st.progress(readiness["readiness_pct"]/100)
    st.caption("Readiness is a transparent checklist of mapped fields and documented metadata. It does not establish measurement validity or biological suitability.")
    with st.expander("Dataset provenance"):
        st.write({"dataset":st.session_state.get("data_name","Active dataset"),
                  "species":st.session_state.get("species","Not specified"),
                  "fingerprint_sha256":readiness["fingerprint"],
                  "records":readiness["n_records"],"variables":readiness["n_variables"],
                  "animals":readiness["n_animals"]})

with tabs[1]:
    st.subheader("Non-destructive quality control")
    st.caption("Flags observations for review. The source dataset is never modified and flagged rows are not automatically removed.")
    numeric = df.select_dtypes(include="number").columns.tolist()
    chosen = st.multiselect("Variables to screen", numeric, default=([outcome] if outcome in numeric else numeric[:5]))
    duration_opts=["— Not selected —"]+df.columns.tolist()
    duration_choice=st.selectbox("Recording duration variable",duration_opts,
        index=(duration_opts.index(duration) if duration in duration_opts else 0))
    min_dur=st.number_input("Minimum duration threshold (seconds)",min_value=0.0,
        value=float(protocol.get("minimum_recording_duration_seconds",0) or 0),step=10.0)
    nonnegative=st.multiselect("Variables expected to be non-negative (optional)",chosen,
        default=([outcome] if outcome in chosen else []),
        help="Only apply this rule where negative values are physically invalid for the documented measurement scale.")
    if st.button("Run QC screening", type="primary"):
        qc=flag_data_quality(df, chosen, None if duration_choice.startswith("—") else duration_choice,
                             min_dur if min_dur>0 else None, nonnegative_columns=nonnegative)
        st.session_state["research_qc_results"]=qc
    qc=st.session_state.get("research_qc_results")
    if qc is not None:
        if qc.empty: st.success("No flags were generated for the selected variables and rules.")
        else:
            st.warning(f"{len(qc):,} variable-level row flags require review.")
            st.dataframe(qc,use_container_width=True,hide_index=True)
            st.download_button("Download QC flags (CSV)",qc.to_csv(index=False).encode(),
                               "methane_qc_flags.csv","text/csv")
    else:
        st.info("Select variables and run QC screening to generate a review queue.")

with tabs[2]:
    st.subheader("Reference-based calibration and agreement")
    st.warning("Only use this analysis when the reference and measured columns are paired observations of the same measurement quantity and compatible units. Correlation alone is not agreement.")
    numeric=df.select_dtypes(include="number").columns.tolist()
    if len(numeric)>=2:
        a,b=st.columns(2)
        ref_col=a.selectbox("Reference measurement",numeric,key="cal_ref")
        measured_col=b.selectbox("Instrument / candidate measurement",[x for x in numeric if x!=ref_col],key="cal_measured")
        if st.button("Calculate calibration diagnostics",type="primary"):
            try:
                result, pairs=calibration_diagnostics(df,ref_col,measured_col)
                st.session_state["calibration_result"]=result
                st.session_state["calibration_pairs"]=pairs
            except Exception as exc: st.error(str(exc))
        if "calibration_result" in st.session_state:
            result=st.session_state["calibration_result"]
            cols=st.columns(4)
            cols[0].metric("Paired observations",f"{result['n_pairs']:,}")
            cols[1].metric("MAE",f"{result['mae']:.4g}")
            cols[2].metric("RMSE",f"{result['rmse']:.4g}")
            cols[3].metric("Mean bias",f"{result['mean_bias_measured_minus_reference']:.4g}")
            st.json(result)
            pairs=st.session_state["calibration_pairs"]
            fig=px.scatter(pairs,x="mean_pair",y="difference_measured_minus_reference",
                           title="Bland–Altman agreement plot", labels={"mean_pair":"Mean of paired measurements","difference_measured_minus_reference":"Measured − reference"})
            fig.add_hline(y=result["mean_bias_measured_minus_reference"],line_dash="dash",annotation_text="Mean bias")
            fig.add_hline(y=result["loa_lower"],line_dash="dot",annotation_text="Lower 95% limits")
            fig.add_hline(y=result["loa_upper"],line_dash="dot",annotation_text="Upper 95% limits")
            st.plotly_chart(fig,use_container_width=True)
            fig2=px.scatter(pairs,x="calibrated_prediction_from_reference",y=measured_col,
                            title="Observed measurements and fitted linear calibration")
            st.plotly_chart(fig2,use_container_width=True)
            st.caption(result["interpretation"])
    else:
        st.info("At least two numeric columns are required.")

with tabs[3]:
    st.subheader("Candidate phenotype evidence matrix")
    numeric=df.select_dtypes(include="number").columns.tolist()
    candidates=st.multiselect("Candidate methane phenotypes",numeric,
        default=([outcome] if outcome in numeric else numeric[:min(4,len(numeric))]))
    animal_opts=["— Not mapped —"]+df.columns.tolist()
    animal_choice=st.selectbox("Animal identifier for repeated-record context",animal_opts,
        index=animal_opts.index(animal) if animal in animal_opts else 0,key="evidence_animal")
    duration_choice=st.selectbox("Recording duration (optional)",["— Not selected —"]+numeric,
        index=(numeric.index(duration)+1 if duration in numeric else 0),key="evidence_duration")
    if st.button("Build phenotype evidence matrix",type="primary"):
        try:
            matrix=phenotype_evidence_matrix(df,candidates,
                None if animal_choice.startswith("—") else animal_choice,
                None if duration_choice.startswith("—") else duration_choice)
            st.session_state["phenotype_evidence_matrix"]=matrix
        except Exception as exc: st.error(str(exc))
    matrix=st.session_state.get("phenotype_evidence_matrix")
    if matrix is not None:
        st.dataframe(matrix,use_container_width=True,hide_index=True)
        st.download_button("Download evidence matrix (CSV)",matrix.to_csv(index=False).encode(),
                           "phenotype_evidence_matrix.csv","text/csv")
        st.info("This matrix is an exploratory screening summary. Repeatability, biological validity, measurement calibration, external validation and study-specific acceptance criteria must be assessed separately.")

with tabs[4]:
    st.subheader("Context-aware analysis recommendations")
    recs=automated_recommendations(df,roles)
    for item in recs:
        with st.container(border=True):
            st.markdown(f"**{item['analysis']}**")
            st.caption(f"{item['priority']} priority")
            st.write(item["reason"])
    st.caption("Recommendations are derived from available columns and repeated-record structure. They are not substitutes for protocol-specific scientific decisions.")
