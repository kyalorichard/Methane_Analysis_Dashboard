import streamlit as st
import pandas as pd
import plotly.express as px
import uuid
from analysis_engine.ui import header, metric_row, render_sidebar_navigation, empty_state
from analysis_engine.standalone_pipeline import run_integrated_analysis, build_analysis_bundle
from platform_core.auth import require_principal
from platform_core.run_registry import save_run, save_run_artifact
from analysis_engine.run_artifacts import build_run_artifact
from platform_core.storage import backend_name

st.set_page_config(page_title="Integrated analysis | Methane Phenotype Analytics",page_icon="🧪",layout="wide")
principal = require_principal()
render_sidebar_navigation()
header("Integrated analysis centre",
       "Run a coordinated scientific analysis and export a portable results package. Configure the design before execution.",
       badge="STANDALONE ANALYSIS")

cloud_backend = backend_name() == "cloud"
active_project_id = st.session_state.get("active_project_id")
if cloud_backend and not active_project_id:
    st.warning("Cloud analysis history requires an active research project. Open or create a project in the Research Workspace before running an analysis.")
    st.page_link("pages/00_Project_Workspace.py", label="Open Research Workspace", icon="🗂️")

df=st.session_state.get("data")
if df is None:
    empty_state("No active dataset","Import a CSV or Excel file from the Overview page or load a dataset from Projects & datasets.")
    st.stop()

restore_cfg = st.session_state.pop("integrated_analysis_restore_config", {})
roles=st.session_state.get("roles",{})
numeric=df.select_dtypes(include="number").columns.tolist()
categorical=[c for c in df.columns if c not in numeric]
animal_default=restore_cfg.get("animal_id") if restore_cfg.get("animal_id") in df.columns else (roles.get("animal_id") if roles.get("animal_id") in df.columns else None)
outcome_default=restore_cfg.get("outcome") if restore_cfg.get("outcome") in numeric else (roles.get("methane") if roles.get("methane") in numeric else (numeric[0] if numeric else None))
if not numeric:
    st.error("No numeric variables were detected. The integrated analysis requires at least one numeric phenotype.")
    st.stop()

metric_row([
    ("RECORDS",f"{len(df):,}","Active dataset"),
    ("VARIABLES",str(df.shape[1]),"Available columns"),
    ("ANIMALS",f"{df[animal_default].nunique():,}" if animal_default else "Not mapped","Animal-level validation"),
    ("CUSTOM PHENOTYPES",str(len(st.session_state.get("phenotype_definitions",{}))),"Current session")
])

st.subheader("1. Configure the analysis")
with st.container(border=True):
    c1,c2,c3=st.columns(3)
    with c1:
        outcome=st.selectbox("Primary phenotype / outcome",numeric,index=numeric.index(outcome_default) if outcome_default in numeric else 0,help="The main numeric trait to describe and evaluate.")
    with c2:
        animal_opts=["— Not mapped —"]+df.columns.tolist()
        animal_choice=st.selectbox("Animal identifier",animal_opts,index=animal_opts.index(animal_default) if animal_default else 0,help="Required for animal-grouped validation and repeated-measures analysis.")
        animal_id=None if animal_choice.startswith("—") else animal_choice
    with c3:
        session_opts=["— None —"]+categorical
        session_default=roles.get("round") if roles.get("round") in categorical else None
        session_choice=st.selectbox("Session / round",session_opts,index=session_opts.index(restore_cfg.get("session_col")) if restore_cfg.get("session_col") in session_opts else (session_opts.index(session_default) if session_default else 0))
        session_col=None if session_choice.startswith("—") else session_choice

    group_opts=["— None —"]+categorical
    group_default=roles.get("breed") if roles.get("breed") in categorical else None
    group_choice=st.selectbox("Primary comparison group",group_opts,index=group_opts.index(restore_cfg.get("group_col")) if restore_cfg.get("group_col") in group_opts else (group_opts.index(group_default) if group_default else 0))
    group_col=None if group_choice.startswith("—") else group_choice
    possible_covars=[c for c in numeric if c!=outcome]
    default_covars=[roles.get("weight")] if roles.get("weight") in possible_covars else []
    covariates=st.multiselect("Continuous covariates for association analysis",possible_covars,default=[c for c in restore_cfg.get("covariates", default_covars) if c in possible_covars])
    st.caption("Group comparisons and covariate associations use one row per animal (numeric variables aggregated by median) when an animal identifier is mapped.")

st.subheader("2. Optional predictive modelling")
run_ml=st.toggle("Include machine-learning benchmark",value=bool(restore_cfg.get("run_ml", False)))
ml_features=[]
ml_models=[]
if run_ml:
    available_features=[c for c in df.columns if c not in {outcome,animal_id} and df[c].nunique(dropna=True)>1]
    default_features=[c for c in available_features if c in numeric][:min(6,len(available_features))]
    ml_features=st.multiselect("Predictor variables",available_features,default=[c for c in restore_cfg.get("ml_features", default_features) if c in available_features],
                               help="Do not include variables that would not be available at the intended prediction time. Exclude identifiers and leakage variables.")
    ml_models=st.multiselect("Models to compare",
        ["Ridge","Elastic Net","Random Forest","Extra Trees","HistGradientBoosting","SVR","KNN"],
        default=[m for m in restore_cfg.get("ml_models", ["Ridge","Random Forest","Extra Trees"]) if m in ["Ridge","Elastic Net","Random Forest","Extra Trees","HistGradientBoosting","SVR","KNN"]])
    if not animal_id:
        st.warning("Predictive benchmarking is disabled until a stable animal identifier is mapped. Record-level random splitting is not used.")
    if not ml_features:
        st.info("Select at least one predictor to run the ML benchmark.")

st.subheader("3. Run integrated analysis")
st.markdown("The run includes data audit, data dictionary, descriptive statistics, phenotype distribution diagnostics, animal-level group profiles, optional group tests, covariate associations, repeated-measure diagnostics and optional animal-grouped ML.")
run=st.button("Run full integrated analysis",type="primary",use_container_width=True,
               disabled=((run_ml and (not animal_id or not ml_features or not ml_models)) or (cloud_backend and not active_project_id)))
if run:
    progress=st.progress(0,text="Preparing dataset audit…")
    try:
        progress.progress(15,text="Auditing data and building descriptive summaries…")
        result=run_integrated_analysis(
            df,dataset_name=st.session_state.get("data_name","active_dataset"),
            species=st.session_state.get("species","other"),outcome=outcome,
            animal_id=animal_id,session_col=session_col,group_col=group_col,
            covariates=covariates,ml_features=ml_features,ml_models=ml_models,
            run_ml=run_ml,seed=int(restore_cfg.get("random_seed", 42)))
        progress.progress(100,text="Analysis completed.")
        st.session_state["latest_integrated_analysis"]=result
        run_id=str(uuid.uuid4())
        result["manifest"]["run_id"]=run_id
        result["manifest"]["project_id"]=st.session_state.get("active_project_id")
        result["manifest"]["dataset_id"]=st.session_state.get("active_dataset_id")
        from analysis_engine.service_registry import get_service
        result["manifest"]["dataset_fingerprint_sha256"]=get_service("dataframe_fingerprint")(df)
        result["manifest"]["measurement_protocol"]=st.session_state.get("measurement_protocol",{})
        result["manifest"]["roles"]=roles
        result["manifest"]["validation_design"]={
            "ml_validation":"animal-grouped GroupKFold" if run_ml else "not run",
            "animal_id":animal_id,"session_column":session_col,
            "independent_unit":"animal" if animal_id else "record-level; independence not assured"
        }
        distribution_fig = px.histogram(df, x=outcome, marginal="box", title=f"Distribution of {outcome}", color_discrete_sequence=["#176B5B"])
        figure_html = distribution_fig.to_html(full_html=True, include_plotlyjs="cdn")
        result["figure_html"] = figure_html
        registry_saved = False
        try:
            save_run(
                run_id, result["manifest"], result["summary"],
                tenant_id=principal.tenant_id,
                project_id=st.session_state.get("active_project_id"),
                dataset_id=st.session_state.get("active_dataset_id"),
                user_subject=principal.subject,
                module_key="integrated_analysis",
            )
            registry_saved = True
            st.session_state["latest_run_registry_status"]="Saved to your project analysis history."
        except Exception as registry_exc:
            st.session_state["latest_run_registry_status"]=f"Analysis completed, but project history could not be saved: {registry_exc}"
        if st.session_state.get("active_project_id") and registry_saved:
            try:
                artifact = build_run_artifact(result, dataset=df, figure_html=figure_html)
                saved = save_run_artifact(
                    run_id, artifact, tenant_id=principal.tenant_id,
                    project_id=st.session_state.get("active_project_id"),
                    user_subject=principal.subject,
                )
                result["artifact_sha256"] = saved["sha256"]
                result["artifact_size_bytes"] = saved["size_bytes"]
                st.session_state["latest_run_artifact_status"] = "Full reproducibility artifact saved to this project."
            except Exception as artifact_exc:
                st.session_state["latest_run_artifact_status"] = f"Run metadata is saved, but full result artifacts could not be retained: {artifact_exc}"
        elif not st.session_state.get("active_project_id"):
            st.session_state["latest_run_artifact_status"] = "Run metadata was saved, but full outputs were not persisted because no project is active. Open a project to retain reusable result artifacts."
        else:
            st.session_state["latest_run_artifact_status"] = "Full result artifacts were not retained because the run could not be registered."
        history=st.session_state.setdefault("analysis_run_history",[])
        history.insert(0,{"timestamp":result["manifest"]["run_timestamp_utc"],
                          "outcome":outcome,"dataset":result["manifest"]["dataset_name"],
                          "run_ml":run_ml,"n_records":len(df)})
        st.success("Integrated analysis completed. Review the results below and export the analysis package.")
        st.caption(st.session_state.get("latest_run_registry_status",""))
        st.caption(st.session_state.get("latest_run_artifact_status",""))
    except Exception as exc:
        progress.empty()
        st.error(f"Analysis could not be completed: {exc}")

result=st.session_state.get("latest_integrated_analysis")
if result:
    st.divider()
    st.subheader("4. Results")
    summary=result["summary"]; manifest=result["manifest"]
    metric_row([
        ("VALID OBSERVATIONS",f"{summary['phenotype_distribution']['n_valid']:,}","Selected phenotype"),
        ("MISSING PHENOTYPE",f"{summary['phenotype_distribution']['missing_pct']:.2f}%","Selected phenotype"),
        ("UNIQUE ANIMALS",str(summary.get("n_independent_animals") or "Not available"),"Independent units"),
        ("ML STATUS", "Included" if summary.get("ml_status","").startswith("Completed") else "Not run / unavailable","Grouped predictive benchmark")
    ])
    tabs=st.tabs(["Data quality","Descriptive results","Group analysis","Repeatability","Associations","ML benchmark","Run manifest"])
    tables=result["tables"]
    with tabs[0]:
        central_qc = st.session_state.get("central_qc_report")
        if central_qc:
            st.caption(f"Central QC engine v{central_qc.get('engine_version')} · fingerprint {str(central_qc.get('dataset_fingerprint',''))[:16]}…")
            st.metric("Central QC screening score", f"{central_qc.get('quality_screening_score', '—')}/100")
            st.dataframe(pd.DataFrame(central_qc.get("findings", [])),use_container_width=True,hide_index=True)
        else:
            st.info("No central QC run is available in this session. Open Data Preparation → Data Quality & QC Centre to run the full QC workflow.")
        st.subheader("Data dictionary")
        st.dataframe(tables["data_dictionary"],use_container_width=True,hide_index=True)
    with tabs[1]:
        st.json(summary["phenotype_distribution"])
        st.dataframe(tables["descriptive_statistics"],use_container_width=True,hide_index=True)
        if result.get("figure_html"):
            import streamlit.components.v1 as components
            components.html(result["figure_html"], height=520, scrolling=True)
        elif df is not None and outcome in df.columns:
            fig=px.histogram(df,x=outcome,marginal="box",title=f"Distribution of {outcome}",color_discrete_sequence=["#176B5B"])
            st.plotly_chart(fig,use_container_width=True)
    with tabs[2]:
        if "group_profile" in tables:
            st.dataframe(tables["group_profile"],use_container_width=True,hide_index=True)
            if "group_test" in summary: st.json(summary["group_test"])
            elif "group_test_error" in summary: st.warning(summary["group_test_error"])
        else: st.info("No comparison group was configured or fewer than two groups were available.")
    with tabs[3]:
        if "repeatability" in summary:
            st.json(summary["repeatability"])
            if not tables["session_summary"].empty: st.dataframe(tables["session_summary"],use_container_width=True,hide_index=True)
            if not tables["paired_session_data"].empty: st.dataframe(tables["paired_session_data"],use_container_width=True,hide_index=True)
        else: st.info("Map animal ID to assess repeatability.")
    with tabs[4]:
        if not tables["associations"].empty: st.dataframe(tables["associations"],use_container_width=True,hide_index=True)
        else: st.info("No valid continuous covariates were selected.")
    with tabs[5]:
        st.write(summary.get("ml_status","Not run"))
        if "ml_benchmark" in tables: st.dataframe(tables["ml_benchmark"],use_container_width=True,hide_index=True)
    with tabs[6]:
        st.json(manifest)
        st.json({"scientific_caveats":summary["scientific_caveats"]})
    bundle=build_analysis_bundle(result,df)
    st.download_button("Download complete analysis package (ZIP)",bundle,
                       file_name="methane_phenotype_analysis_package.zip",
                       mime="application/zip",type="primary",use_container_width=True)
    st.caption("The ZIP contains an Excel workbook, CSV tables, HTML summary, JSON run manifest and the analysis dataset. It does not contain fitted model binaries. A separate project artifact is retained for reopening the results.")
else:
    st.info("Configure the analysis and select **Run full integrated analysis**. Results will appear here.")
