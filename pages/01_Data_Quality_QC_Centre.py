from __future__ import annotations
import io, json, zipfile
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from analysis_engine.ui import header, metric_row, render_sidebar_navigation, empty_state
from analysis_engine.quality_control import (run_quality_control, findings_frame, dataframe_fingerprint,
    configured_range_mask, apply_range_disposition)
from platform_core.auth import require_principal

st.set_page_config(page_title="Data Quality & QC Centre | Methane Phenotype Analytics", page_icon="🧹", layout="wide")
require_principal(); render_sidebar_navigation()
header("Data Quality & QC Centre", "One auditable location for dataset integrity, phenotype screening, repeated-measure checks, protocol rules and QC decisions.", badge="CENTRAL DATA GOVERNANCE")
df = st.session_state.get("data")
if df is None:
    empty_state("No active dataset", "Open Projects & datasets and import or select a dataset before running QC.")
    st.stop()

roles = st.session_state.get("roles", {}) or {}
cols = list(df.columns)
animal_default = roles.get("animal_id") if roles.get("animal_id") in cols else None
c1,c2,c3 = st.columns(3)
with c1: animal_id = st.selectbox("Animal identifier (optional)", ["— None —"] + cols, index=(cols.index(animal_default)+1 if animal_default else 0), key="central_qc_animal")
with c2: time_col = st.selectbox("Time / visit variable (optional)", ["— None —"] + cols, key="central_qc_time")
with c3: outlier_method = st.selectbox("Outlier screening", ["IQR"], key="central_qc_outlier_method")
multiplier = st.select_slider("IQR fence multiplier", options=[1.0,1.5,2.0,3.0], value=1.5, key="central_qc_iqr")
animal_id = None if animal_id == "— None —" else animal_id
time_col = None if time_col == "— None —" else time_col

rules = st.session_state.get("central_qc_rules", {})
with st.expander("Configure study-specific / instrument limits", expanded=False):
    numeric = df.select_dtypes(include="number").columns.tolist()
    chosen = st.multiselect("Variables with protocol limits", numeric, default=[c for c in rules if c in numeric], key="central_qc_rule_vars")
    new_rules = {}
    for col in chosen:
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        default_min = float(vals.min()) if len(vals) else 0.0
        default_max = float(vals.max()) if len(vals) else 1.0
        old = rules.get(col, {})
        a,b,c = st.columns([1,1,2])
        with a: lo = st.number_input(f"{col} minimum", value=float(old.get("min", default_min)), key=f"central_qc_min_{col}")
        with b: hi = st.number_input(f"{col} maximum", value=float(old.get("max", default_max)), key=f"central_qc_max_{col}")
        with c: rationale = st.text_input(f"{col} rationale / source", value=str(old.get("source", "Study protocol / instrument specification")), key=f"central_qc_source_{col}")
        if lo > hi: st.error(f"{col}: minimum must not exceed maximum.")
        else: new_rules[col] = {"min": lo, "max": hi, "source": rationale}
    if st.button("Save QC rule configuration", key="save_central_qc_rules"):
        st.session_state["central_qc_rules"] = new_rules
        st.success("QC rules saved in the active browser session.")
        st.rerun()

fingerprint = dataframe_fingerprint(df)
report = st.session_state.get("central_qc_report")
if not report or report.get("dataset_fingerprint") != fingerprint or report.get("rules") != rules or report.get("settings", {}).get("iqr_multiplier") != float(multiplier) or report.get("settings", {}).get("animal_id") != animal_id or report.get("settings", {}).get("time_col") != time_col:
    report = run_quality_control(df, rules=rules, animal_id=animal_id, time_col=time_col, outlier_method=outlier_method, iqr_multiplier=multiplier)
    st.session_state["central_qc_report"] = report

left,right = st.columns([1,3])
with left:
    if st.button("Run / refresh full QC", type="primary", use_container_width=True, key="run_full_central_qc"):
        report = run_quality_control(df, rules=rules, animal_id=animal_id, time_col=time_col, outlier_method=outlier_method, iqr_multiplier=multiplier)
        st.session_state["central_qc_report"] = report
        st.session_state["central_qc_report_fingerprint"] = fingerprint
        try:
            import uuid
            from platform_core import run_registry
            principal = require_principal()
            run_registry.save_run(str(uuid.uuid4()),
                {"run_timestamp_utc": report["created_utc"], "dataset_name": st.session_state.get("active_dataset_name") or st.session_state.get("data_name"),
                 "dataset_fingerprint_sha256": fingerprint, "species": st.session_state.get("species"), "module_key": "unified_data_quality_qc"},
                {"qc_report": report, "decision_count": len(st.session_state.get("central_qc_history", []))},
                status="completed", tenant_id=principal.tenant_id, project_id=st.session_state.get("active_project_id"),
                dataset_id=st.session_state.get("active_dataset_id"), user_subject=principal.subject, module_key="unified_data_quality_qc")
            st.session_state["central_qc_registry_status"] = "QC run saved to project-scoped analysis history."
        except Exception as exc:
            st.session_state["central_qc_registry_status"] = f"QC run remains available in this session; durable registry save unavailable: {exc}"
        st.rerun()
with right:
    st.caption(f"Dataset fingerprint: `{fingerprint[:16]}…` · Engine v{report['engine_version']} · {report['created_utc']}")

sev = report["severity_counts"]
metric_row([("SCREENING SCORE",f"{report['quality_screening_score']}/100","Prioritisation aid; not a validated quality metric"),
           ("CRITICAL / HIGH",f"{sev['critical']} / {sev['high']}","Review before inferential use"),
           ("WARNINGS",f"{sev['warning']}","Investigate; no automatic exclusion"),
           ("RECORDS / VARIABLES",f"{report['n_records']:,} / {report['n_variables']:,}","Active analysis dataset")])
if report["blocking_issues"]: st.error("Critical structural issues detected. Resolve or document them before proceeding with formal analysis.")
elif sev["high"]: st.warning("High-priority QC findings require investigator review.")
else: st.success("No critical structural blockers detected by the current screening rules.")

findings = findings_frame(report)
tabs = st.tabs(["QC overview & findings", "Data integrity & missingness", "Phenotype screening", "Repeated-measure QC", "QC decisions & history", "Reports & exports"])
with tabs[0]:
    st.subheader("Findings by severity")
    if findings.empty: st.success("No findings were generated by the current checks.")
    else:
        st.dataframe(findings.sort_values(["severity","n_flagged"], ascending=[True,False]), use_container_width=True, hide_index=True)
        st.caption("Severity is a triage label. It does not establish that a biological measurement is invalid.")
with tabs[1]:
    st.subheader("Structural integrity")
    metric_row([("EXACT DUPLICATES",f"{report['duplicate_rows']:,}","Review before removing"),("MISSING CELLS",f"{report['missing_cells']:,}","Missingness is not imputed"),("EMPTY ROWS",f"{int(df.isna().all(axis=1).sum()):,}","Entirely empty records")])
    miss = pd.DataFrame({"variable":df.columns.astype(str),"dtype":[str(x) for x in df.dtypes],"missing_n":df.isna().sum().values,"missing_percent":(df.isna().mean()*100).round(2).values,"unique_n":df.nunique(dropna=True).values}).sort_values("missing_percent",ascending=False)
    st.dataframe(miss,use_container_width=True,hide_index=True)
    st.caption("Missingness is described, not automatically imputed. Assess the missing-data mechanism and analysis-specific consequences.")
with tabs[2]:
    st.subheader("Phenotype distributions and potential outliers")
    numeric = df.select_dtypes(include="number").columns.tolist()
    if numeric:
        phenotype = st.selectbox("Phenotype variable",numeric,key="central_qc_phenotype")
        x = pd.to_numeric(df[phenotype],errors="coerce").dropna()
        a,b,c = st.columns(3); a.metric("Observed",f"{len(x):,}"); b.metric("Unique values",f"{x.nunique():,}"); c.metric("Missing",f"{df[phenotype].isna().sum():,}")
        if len(x):
            st.write(x.describe().to_frame("summary"))
            try:
                import plotly.express as px
                st.plotly_chart(px.histogram(x, nbins=30, title=f"Distribution: {phenotype}"),use_container_width=True)
                st.plotly_chart(px.box(x, points="outliers", title=f"Potential outliers: {phenotype}"),use_container_width=True)
            except Exception as exc: st.info(f"Distribution plots unavailable: {exc}")
        st.caption("IQR flags are distribution-based screening signals, not biological reference intervals. Use protocol- and species-specific limits where validated.")
    else: st.info("No numeric phenotype variables are available.")
with tabs[3]:
    st.subheader("Animal-level repeated-measure structure")
    if animal_id:
        summary = report.get("animal_repeated_measure_summary", {})
        if summary: metric_row([("ANIMALS",f"{summary['n_animals']:,}","Unique non-missing identifiers"),("REPEATED ANIMALS",f"{summary['repeated_animals']:,}","More than one record"),("SINGLE-RECORD ANIMALS",f"{summary['single_record_animals']:,}","One record only"),("MAX RECORDS / ANIMAL",str(summary['max_records_per_animal']),"Observed maximum")])
        if time_col:
            tmp=df[[animal_id,time_col]].dropna().copy(); st.write("Records by animal (first 100)")
            counts=tmp.groupby(animal_id,dropna=True).size().rename("records").reset_index().sort_values("records",ascending=False)
            st.dataframe(counts.head(100),use_container_width=True,hide_index=True)
        else: st.info("Select a time/visit variable above to assess duplicate animal-time keys.")
    else: st.info("Select the animal identifier above to activate repeated-measure checks.")
with tabs[4]:
    st.subheader("Range-validation decisions")
    st.write("For observations outside configured variable limits, choose whether to retain, exclude from an analysis copy, estimate a replacement, or winsorize selected values. The source dataset is never modified by these actions.")
    range_variables = [c for c in rules if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    working = st.session_state.get("central_qc_working_data")
    working_source_fp = st.session_state.get("central_qc_working_source_fingerprint")
    if working is None or working_source_fp != fingerprint:
        working = df.copy(deep=True)
        st.session_state["central_qc_working_data"] = working
        st.session_state["central_qc_working_source_fingerprint"] = fingerprint
        st.session_state["central_qc_working_actions"] = []
    if not range_variables:
        st.info("Configure at least one numeric variable range before using Keep / Drop / Estimate / Winsorize.")
    else:
        selected_variable = st.selectbox("Variable with configured limits", range_variables, key="central_qc_disposition_variable")
        selected_rule = rules[selected_variable]
        current_mask = configured_range_mask(working, selected_variable, selected_rule)
        flagged_positions = [int(x) for x in __import__("numpy").flatnonzero(current_mask.to_numpy())]
        st.caption(f"Configured range: {selected_rule.get('min', '-∞')} to {selected_rule.get('max', '∞')} · {len(flagged_positions):,} currently flagged observation(s) in the working copy")
        if flagged_positions:
            preview_rows = []
            for pos in flagged_positions:
                row = {"row_position": pos, "original/current_value": working[selected_variable].iloc[pos]}
                if animal_id and animal_id in working.columns: row["animal_id"] = working[animal_id].iloc[pos]
                if time_col and time_col in working.columns: row["time"] = working[time_col].iloc[pos]
                preview_rows.append(row)
            st.dataframe(pd.DataFrame(preview_rows).head(500), use_container_width=True, hide_index=True)
            if len(flagged_positions) > 500: st.caption("Showing the first 500 flagged observations; selection below can include all flagged rows.")
            row_choices = [str(x) for x in flagged_positions]
            default_choices = row_choices if len(row_choices) <= 100 else row_choices[:100]
            chosen_rows = st.multiselect("Select flagged row positions", row_choices, default=default_choices, key="central_qc_disposition_rows")
            action_label = st.radio("Decision", ["Keep", "Drop from analysis copy", "Estimate replacement", "Winsorize selected observations"], horizontal=True, key="central_qc_disposition_action")
            method = None
            group_col = None
            lower_q = 0.05
            upper_q = 0.95
            if action_label == "Winsorize selected observations":
                st.caption("Winsorization caps selected flagged values at empirical quantile thresholds calculated from the remaining valid observations. It retains the rows but changes selected values in the QC working copy.")
                q1, q2 = st.columns(2)
                with q1:
                    lower_q = st.number_input("Lower quantile", min_value=0.0, max_value=0.49, value=0.05, step=0.01, key="central_qc_winsor_lower")
                with q2:
                    upper_q = st.number_input("Upper quantile", min_value=0.51, max_value=1.0, value=0.95, step=0.01, key="central_qc_winsor_upper")
                if lower_q >= upper_q:
                    st.warning("Lower quantile must be smaller than upper quantile.")
            if action_label == "Estimate replacement":
                method = st.selectbox("Estimation method", ["Global median", "Group median", "Within-animal interpolation"], key="central_qc_estimation_method")
                if method == "Group median":
                    group_options = [c for c in working.columns if c != selected_variable]
                    group_col = st.selectbox("Grouping variable", group_options, key="central_qc_estimation_group")
                elif method == "Within-animal interpolation":
                    if not animal_id or not time_col:
                        st.warning("Select animal identifier and time/visit variables at the top of this page before using within-animal interpolation.")
            disposition_rationale = st.text_area("Decision rationale / protocol reference", key="central_qc_disposition_rationale", placeholder="Explain why these observations are retained, excluded or estimated.")
            apply_disabled = (not chosen_rows or not disposition_rationale.strip()
                or (action_label == "Estimate replacement" and method == "Within-animal interpolation" and (not animal_id or not time_col))
                or (action_label == "Winsorize selected observations" and lower_q >= upper_q))
            if st.button("Apply decision to QC working copy", type="primary", disabled=apply_disabled, key="apply_central_qc_disposition"):
                try:
                    updated, action_record = apply_range_disposition(
                        working, variable=selected_variable,
                        row_positions=[int(x) for x in chosen_rows],
                        action={"Keep": "keep", "Drop from analysis copy": "drop", "Estimate replacement": "estimate", "Winsorize selected observations": "winsorize"}[action_label],
                        method=method, group_col=group_col, animal_id=animal_id, time_col=time_col,
                        valid_mask=~current_mask, lower_quantile=lower_q, upper_quantile=upper_q,
                    )
                    action_record.update({"recorded_utc": datetime.now(timezone.utc).isoformat(),
                        "project_id": st.session_state.get("active_project_id"),
                        "dataset_fingerprint": fingerprint, "rationale": disposition_rationale.strip(),
                        "configured_range": {"min": selected_rule.get("min"), "max": selected_rule.get("max"), "source": selected_rule.get("source")}})
                    st.session_state["central_qc_working_data"] = updated
                    st.session_state.setdefault("central_qc_working_actions", []).append(action_record)
                    st.session_state.setdefault("central_qc_history", []).append(action_record)
                    st.session_state.pop("central_qc_disposition_rows", None)
                    st.success(f"{action_label} decision applied to {len(chosen_rows)} selected observation(s) in the QC working copy.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Decision could not be applied: {exc}")
        else:
            st.success("No observations currently violate this configured range in the QC working copy.")
    working = st.session_state.get("central_qc_working_data")
    actions = st.session_state.get("central_qc_working_actions", [])
    if working is not None and working_source_fp == fingerprint:
        metric_row([("SOURCE RECORDS", f"{len(df):,}", "Unmodified source snapshot"),
                    ("WORKING RECORDS", f"{len(working):,}", "After explicit QC actions"),
                    ("QC ACTIONS", f"{len(actions):,}", "Recorded in audit history")])
        if actions:
            st.dataframe(pd.DataFrame(actions)[[c for c in ["recorded_utc", "action", "variable", "row_positions", "method", "lower_quantile", "upper_quantile", "lower_bound", "upper_bound", "records_before", "records_after", "rationale"] if c in pd.DataFrame(actions).columns]], use_container_width=True, hide_index=True)
        c_apply, c_reset = st.columns(2)
        with c_apply:
            if st.button("Activate QC working copy for analysis", type="primary", use_container_width=True, disabled=not actions, key="activate_central_qc_working_copy"):
                st.session_state["data"] = working.copy(deep=True)
                st.session_state["central_qc_activated_data"] = working.copy(deep=True)
                st.session_state["central_qc_activated_source_fingerprint"] = fingerprint
                st.session_state.setdefault("cleaning_log", []).append({
                    "operation": "central_qc_dispositions", "actions": actions,
                    "records_before": len(df), "records_after": len(working),
                    "source_fingerprint": fingerprint, "timestamp_utc": datetime.now(timezone.utc).isoformat()})
                st.session_state["data_name"] = f"{st.session_state.get('data_name', 'dataset')}_qc_adjusted"
                st.session_state["central_qc_report"] = None
                st.session_state["central_qc_working_data"] = None
                st.success("QC-adjusted analysis copy activated. Save it as a new project dataset version in Data Preparation Studio to persist it.")
                st.rerun()
        with c_reset:
            if st.button("Reset QC working copy", use_container_width=True, key="reset_central_qc_working_copy"):
                st.session_state["central_qc_working_data"] = df.copy(deep=True)
                st.session_state["central_qc_working_actions"] = []
                st.rerun()
    st.divider()
    st.subheader("Document other investigator decisions")
    st.caption("General QC decisions below are annotations; range actions above operate only on the separate QC working copy.")
    finding_options = [f"{r['check']} | {r['variable']} | {r['n_flagged']}" for r in report["findings"]]
    selected = st.selectbox("Finding", finding_options or ["No findings"], key="central_qc_decision_finding")
    decision = st.selectbox("Decision",["Reviewed — retain","Flag for follow-up","Corrected in prepared dataset","Exclude from analysis copy","Accepted with justification"],key="central_qc_decision")
    rationale = st.text_area("Rationale / evidence",key="central_qc_rationale",placeholder="Document protocol reference, source verification, correction or exclusion rationale.")
    if st.button("Record QC decision",disabled=not finding_options or not rationale.strip(),key="record_central_qc_decision"):
        history=st.session_state.setdefault("central_qc_history",[])
        history.append({"recorded_utc":datetime.now(timezone.utc).isoformat(),"project_id":st.session_state.get("active_project_id"),"dataset_name":st.session_state.get("active_dataset_name") or st.session_state.get("data_name"),"dataset_fingerprint":fingerprint,"finding":selected,"decision":decision,"rationale":rationale.strip()})
        st.success("QC decision added to the session audit history.")
        try:
            import uuid
            from platform_core import run_registry
            principal = require_principal()
            run_registry.save_run(str(uuid.uuid4()),
                {"run_timestamp_utc": history[-1]["recorded_utc"], "dataset_name": history[-1]["dataset_name"],
                 "dataset_fingerprint_sha256": fingerprint, "species": st.session_state.get("species")},
                {"qc_report": report, "decision": history[-1]}, status="completed",
                tenant_id=principal.tenant_id, project_id=st.session_state.get("active_project_id"),
                dataset_id=st.session_state.get("active_dataset_id"), user_subject=principal.subject, module_key="unified_data_quality_qc")
            st.session_state["central_qc_registry_status"] = "QC decision saved to project-scoped analysis history."
        except Exception as exc:
            st.session_state["central_qc_registry_status"] = f"Decision recorded in this session; durable registry save unavailable: {exc}"
    history=st.session_state.get("central_qc_history",[])
    if history: st.dataframe(pd.DataFrame(history),use_container_width=True,hide_index=True)
    else: st.info("No investigator decisions recorded in this browser session.")
    if st.session_state.get("central_qc_registry_status"): st.caption(st.session_state["central_qc_registry_status"])
    try:
        from platform_core import run_registry
        principal = require_principal()
        saved_runs = run_registry.list_runs(limit=100, tenant_id=principal.tenant_id,
            project_id=st.session_state.get("active_project_id"), user_subject=principal.subject)
        qc_runs=[]
        for item in saved_runs:
            if item.get("module_key") == "unified_data_quality_qc":
                qc_runs.append({"run_id":item.get("run_id"),"created_utc":item.get("created_utc"),"dataset_name":item.get("dataset_name"),"status":item.get("status"),"fingerprint":item.get("dataset_fingerprint")})
        if qc_runs:
            st.subheader("Saved project QC run history")
            st.dataframe(pd.DataFrame(qc_runs),use_container_width=True,hide_index=True)
    except Exception as exc:
        st.caption(f"Project QC history is not available: {exc}")
with tabs[5]:
    st.subheader("Download a reproducible QC package")
    st.write("The package contains the QC report, findings table, variable-level missingness profile, investigator decisions and a manifest with dataset fingerprint and engine settings. When available, it also includes the separate QC-adjusted analysis copy and its disposition audit. The original source dataset is not modified.")
    history=st.session_state.get("central_qc_history",[])
    manifest={"artifact_type":"methane-unified-qc-report","artifact_version":1,"project_id":st.session_state.get("active_project_id"),"project_name":st.session_state.get("active_project_name"),"dataset_name":st.session_state.get("active_dataset_name") or st.session_state.get("data_name"),"dataset_fingerprint":fingerprint,"qc_report":report,"decisions":history,"created_utc":datetime.now(timezone.utc).isoformat(),"limitations":"QC flags are screening evidence and require investigator review. The source dataset is never modified; explicit Keep, Drop, Estimate and Winsorize actions affect only the separate QC working copy."}
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json",json.dumps(manifest,indent=2,default=str))
        z.writestr("qc_findings.csv",findings.to_csv(index=False))
        z.writestr("missingness_profile.csv",miss.to_csv(index=False) if 'miss' in locals() else pd.DataFrame({"variable":df.columns.astype(str),"missing_n":df.isna().sum().values,"missing_percent":(df.isna().mean()*100).round(2).values}).to_csv(index=False))
        z.writestr("investigator_decisions.csv",pd.DataFrame(history).to_csv(index=False) if history else "")
        qc_working = st.session_state.get("central_qc_working_data")
        qc_working_actions = st.session_state.get("central_qc_working_actions", [])
        if qc_working is not None and st.session_state.get("central_qc_working_source_fingerprint") == fingerprint:
            z.writestr("qc_adjusted_analysis_copy.csv", qc_working.to_csv(index=False))
            z.writestr("qc_disposition_actions.json", json.dumps(qc_working_actions, indent=2, default=str))
        elif st.session_state.get("central_qc_activated_data") is not None:
            z.writestr("qc_adjusted_analysis_copy.csv", st.session_state["central_qc_activated_data"].to_csv(index=False))
            z.writestr("qc_disposition_actions.json", json.dumps(st.session_state.get("central_qc_working_actions", []), indent=2, default=str))
    st.download_button("Download QC reproducibility package (.zip)",buf.getvalue(),file_name="methane_unified_qc_report.zip",mime="application/zip",type="primary")
    st.download_button("Download findings only (.csv)",findings.to_csv(index=False).encode(),file_name="qc_findings.csv",mime="text/csv")
    st.caption("QC runs and decisions are also registered in project-scoped analysis history when the configured local/cloud metadata backend is available. The downloadable archive remains the portable, self-contained record.")

st.divider()
st.info("Workflow: review findings → verify source/protocol → record a decision → make any correction or exclusion only in Data Preparation Studio → rerun QC on the resulting dataset version.")
