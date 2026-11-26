import streamlit as st
import pandas as pd
import plotly.express as px
from analysis_engine.ui import header, metric_row, render_sidebar_navigation, empty_state
from analysis_engine.advanced_research import (
    fit_allometric_scaling,
    cluster_bootstrap_mean_difference,
)
from platform_core.auth import require_principal
from analysis_engine.service_registry import get_service

st.set_page_config(page_title="Advanced inference | Methane Phenotype Analytics", page_icon="📐", layout="wide")
require_principal()
render_sidebar_navigation()
header("Advanced inference & scaling", "Conditional quantiles, allometric relationships and animal-level bootstrap contrasts.", badge="RESEARCH 5.1")
df = st.session_state.get("data")
if df is None or df.empty:
    empty_state("No active dataset", "Load a study dataset from the project workspace to use advanced inference.")
    st.stop()

numeric = df.select_dtypes(include="number").columns.tolist()
all_cols = df.columns.tolist()
roles = st.session_state.get("roles", {})
if not numeric:
    st.warning("No numeric variables are available.")
    st.stop()
tabs = st.tabs(["Quantile regression", "Allometric scaling", "Animal-level bootstrap contrast", "Population-average GEE", "Missing-data sensitivity", "Multiple-testing correction"])

with tabs[0]:
    st.subheader("Conditional quantile regression")
    st.caption("Estimates conditional quantiles (for example, the median) rather than the conditional mean. Standard errors are asymptotic; inspect convergence and sparse factor levels.")
    y = st.selectbox("Outcome", numeric, key="qreg_y")
    predictors = st.multiselect("Predictors", [c for c in all_cols if c != y], key="qreg_x")
    q = st.slider("Target quantile", 0.05, 0.95, 0.50, 0.05, key="qreg_q")
    if st.button("Fit quantile regression", type="primary", key="qreg_fit"):
        try:
            model, used = get_service("fit_quantile_regression")(df, y, predictors, q, st.session_state.get("analysis_settings", {}))
            st.session_state["qreg_result"] = {"summary": model.summary().as_text(), "n": len(used), "params": model.params.to_frame("coefficient").reset_index(names="term"), "q": q}
        except Exception as exc:
            st.error(str(exc))
    res = st.session_state.get("qreg_result")
    if res:
        metric_row([("N", f"{res['n']:,}", "Complete observations"), ("QUANTILE", f"{res['q']:.2f}", "Conditional quantile fitted")])
        st.dataframe(res["params"], use_container_width=True, hide_index=True)
        st.code(res["summary"])
        st.download_button("Download quantile model summary", res["summary"], "quantile_regression_summary.txt")

with tabs[1]:
    st.subheader("Allometric scaling")
    st.caption("Fits a log–log relationship using positive paired measurements. The slope is the allometric scaling exponent; it is not automatically an efficiency or causal effect.")
    y = st.selectbox("Response trait (positive values)", numeric, key="allo_y")
    x = st.selectbox("Size / scaling trait (positive values)", [c for c in numeric if c != y], key="allo_x") if len(numeric) > 1 else None
    if x and st.button("Estimate scaling exponent", type="primary", key="allo_fit"):
        try:
            st.session_state["allo_result"] = fit_allometric_scaling(df, y, x)
        except Exception as exc:
            st.error(str(exc))
    res = st.session_state.get("allo_result")
    if res:
        metric_row([("N", f"{res['n']:,}", "Positive paired observations"), ("EXPONENT", f"{res['scaling_exponent']:.3f}", "Log-log slope"), ("95% CI", f"{res['exponent_ci_low']:.3f} to {res['exponent_ci_high']:.3f}", "HC3 confidence interval"), ("R²", f"{res['r_squared']:.3f}", "In-sample fit")])
        used = res["used_data"]
        fig = px.scatter(used, x=x, y=y, log_x=True, log_y=True, trendline="ols", title="Allometric relationship (log scales)")
        st.plotly_chart(fig, use_container_width=True)
        st.code(res["summary"])
        st.caption(res["note"])
        st.download_button("Download allometric model summary", res["summary"], "allometric_scaling_summary.txt")

with tabs[2]:
    st.subheader("Animal-level bootstrap group contrast")
    st.caption("Repeated observations are averaged within animal before resampling. This avoids treating repeated records as independent animals.")
    animal_default = roles.get("animal_id") if roles.get("animal_id") in all_cols else all_cols[0]
    animal = st.selectbox("Animal identifier", all_cols, index=all_cols.index(animal_default), key="boot_animal")
    group = st.selectbox("Comparison group", [c for c in all_cols if c != animal], key="boot_group")
    y = st.selectbox("Outcome", numeric, key="boot_y")
    levels = df[group].dropna().unique().tolist()
    if len(levels) < 2:
        st.warning("The selected grouping variable has fewer than two observed levels.")
    else:
        a = st.selectbox("Group A", levels, index=0, key="boot_a")
        b_options = [v for v in levels if v != a]
        b = st.selectbox("Group B", b_options, key="boot_b")
        reps = st.select_slider("Bootstrap replicates", options=[500, 1000, 2000, 5000], value=2000, key="boot_reps")
        if st.button("Estimate animal-level mean difference", type="primary", key="boot_run"):
            try:
                st.session_state["boot_result"] = cluster_bootstrap_mean_difference(df, y, group, a, b, animal, reps)
            except Exception as exc:
                st.error(str(exc))
    res = st.session_state.get("boot_result")
    if res:
        metric_row([("ANIMALS A", f"{res['n_animals_a']:,}", "Independent animal units"), ("ANIMALS B", f"{res['n_animals_b']:,}", "Independent animal units"), ("A − B", f"{res['difference_a_minus_b']:.4g}", "Difference in animal-level means"), ("95% CI", f"{res['ci_low']:.4g} to {res['ci_high']:.4g}", "Percentile bootstrap interval")])
        fig = px.histogram(x=res["bootstrap_distribution"], nbins=45, title="Bootstrap distribution of mean difference")
        fig.add_vline(x=0, line_dash="dash")
        st.plotly_chart(fig, use_container_width=True)
        st.json({k: v for k, v in res.items() if k not in {"bootstrap_distribution"}})
        st.caption(res["note"])


with tabs[3]:
    st.subheader("Population-average inference")
    st.caption("GEE estimates marginal (population-average) associations while accounting for within-animal correlation. Cluster-robust OLS is available as a linear-model sensitivity analysis.")
    animal_default = roles.get("animal_id") if roles.get("animal_id") in all_cols else all_cols[0]
    cluster = st.selectbox("Independent cluster / animal ID", all_cols, index=all_cols.index(animal_default), key="gee_cluster")
    y = st.selectbox("Outcome", numeric, key="gee_y")
    predictors = st.multiselect("Predictors", [c for c in all_cols if c not in {cluster, y}], key="gee_predictors")
    covariance = st.radio("GEE working correlation", ["exchangeable", "independence"], horizontal=True, key="gee_cov")
    gee_col, ols_col = st.columns(2)
    if gee_col.button("Fit population-average GEE", type="primary", key="gee_fit"):
        try:
            model, used, audit = get_service("population_average_gee")(df, y, predictors, cluster, covariance)
            st.session_state["phase5_gee_result"] = {"summary": model.summary().as_text(), "params": model.params.to_frame("coefficient").reset_index(names="term"), "audit": audit}
        except Exception as exc:
            st.error(str(exc))
    if ols_col.button("Fit cluster-robust OLS", key="cluster_ols_fit"):
        try:
            model, used, audit = get_service("cluster_robust_ols")(df, y, predictors, cluster)
            st.session_state["phase5_cluster_ols_result"] = {"summary": model.summary().as_text(), "params": model.params.to_frame("coefficient").reset_index(names="term"), "audit": audit}
        except Exception as exc:
            st.error(str(exc))
    for key, label in [("phase5_gee_result", "GEE results"), ("phase5_cluster_ols_result", "Cluster-robust OLS results")]:
        result = st.session_state.get(key)
        if result:
            st.markdown(f"**{label}**")
            metric_row([("RECORDS", f"{result['audit']['n_records']:,}", "Complete observations"), ("CLUSTERS", f"{result['audit']['n_clusters']:,}", "Independent clusters")])
            st.dataframe(result["params"], use_container_width=True, hide_index=True)
            st.code(result["summary"])
            st.warning(result["audit"]["caution"])
            st.download_button(f"Download {label} summary", result["summary"], f"{key}_summary.txt", key=f"download_{key}")

with tabs[4]:
    st.subheader("Missing-data audit and delta sensitivity")
    st.caption("Describe missingness and assess how a range of hypothetical shifts in missing outcomes would change a two-group contrast. This is not a substitute for a justified MAR/MNAR model.")
    missing_cols = st.multiselect("Variables to audit", all_cols, default=numeric[:min(3, len(numeric))], key="miss_cols")
    animal_default = roles.get("animal_id") if roles.get("animal_id") in all_cols else all_cols[0]
    miss_cluster = st.selectbox("Optional animal / cluster identifier", ["(none)"] + all_cols, index=(all_cols.index(animal_default) + 1), key="miss_cluster")
    if st.button("Audit missingness", key="miss_audit"):
        try:
            audit, patterns, cluster_summary, summary = get_service("missingness_audit")(df, missing_cols, None if miss_cluster == "(none)" else miss_cluster)
            st.session_state["phase5_missing_result"] = (audit, patterns, cluster_summary, summary)
        except Exception as exc:
            st.error(str(exc))
    miss_res = st.session_state.get("phase5_missing_result")
    if miss_res:
        audit, patterns, cluster_summary, summary = miss_res
        metric_row([("RECORDS", f"{summary['n_records']:,}", "Input records"), ("COMPLETE CASES", f"{summary['complete_case_percent']:.1f}%", f"{summary['complete_case_records']:,} records")])
        st.dataframe(audit, use_container_width=True, hide_index=True)
        st.dataframe(patterns.head(20), use_container_width=True, hide_index=True)
        if cluster_summary is not None:
            st.dataframe(cluster_summary, use_container_width=True, hide_index=True)
        st.info(summary["note"])
    st.divider()
    st.markdown("**Outcome delta-adjustment sensitivity**")
    sens_y = st.selectbox("Outcome with possible missing values", numeric, key="delta_y")
    sens_group = st.selectbox("Two-group variable", [c for c in all_cols if c != sens_y], key="delta_group")
    sens_levels = df[sens_group].dropna().unique().tolist()
    if len(sens_levels) >= 2:
        sens_a = st.selectbox("Group A", sens_levels, key="delta_a")
        sens_b = st.selectbox("Group B", [v for v in sens_levels if v != sens_a], key="delta_b")
        if st.button("Run delta sensitivity", key="delta_run"):
            try:
                table, note = get_service("delta_missing_outcome_sensitivity")(df, sens_y, sens_group, sens_a, sens_b)
                st.session_state["phase5_delta_result"] = (table, note)
            except Exception as exc:
                st.error(str(exc))
    delta_res = st.session_state.get("phase5_delta_result")
    if delta_res:
        st.dataframe(delta_res[0], use_container_width=True, hide_index=True)
        st.caption(delta_res[1]["note"])
        st.download_button("Download delta sensitivity table", delta_res[0].to_csv(index=False), "missing_outcome_delta_sensitivity.csv")

with tabs[5]:
    st.subheader("Multiple-comparison correction")
    st.caption("Adjust a family of p-values using Benjamini–Hochberg FDR, Benjamini–Yekutieli, Holm or Bonferroni. Define the family of hypotheses before interpreting adjusted values.")
    p_upload = st.file_uploader("Upload CSV containing a p_value column", type=["csv"], key="p_adjust_upload")
    method = st.selectbox("Adjustment method", ["fdr_bh", "fdr_by", "holm", "bonferroni", "sidak", "holm-sidak"], format_func=lambda x: {"fdr_bh":"Benjamini–Hochberg FDR", "fdr_by":"Benjamini–Yekutieli FDR", "holm":"Holm step-down", "bonferroni":"Bonferroni", "sidak":"Šidák", "holm-sidak":"Holm–Šidák"}[x], key="p_adjust_method")
    if p_upload is not None and st.button("Adjust p-values", type="primary", key="p_adjust_run"):
        try:
            p_data = pd.read_csv(p_upload)
            adjusted = get_service("multiple_testing_adjustment")(p_data, "p_value", method)
            st.session_state["phase5_adjusted_p"] = adjusted
        except Exception as exc:
            st.error(str(exc))
    adjusted = st.session_state.get("phase5_adjusted_p")
    if adjusted is not None:
        st.dataframe(adjusted, use_container_width=True, hide_index=True)
        st.download_button("Download adjusted p-values", adjusted.to_csv(index=False), "multiple_testing_adjusted_results.csv")
