import streamlit as st
import pandas as pd
import plotly.express as px
from analysis_engine.ui import header, metric_row, render_sidebar_navigation, empty_state
from analysis_engine.advanced_research import (
    fit_quantile_regression, fit_allometric_scaling,
    cluster_bootstrap_mean_difference,
)
from platform_core.auth import require_principal

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
tabs = st.tabs(["Quantile regression", "Allometric scaling", "Animal-level bootstrap contrast"])

with tabs[0]:
    st.subheader("Conditional quantile regression")
    st.caption("Estimates conditional quantiles (for example, the median) rather than the conditional mean. Standard errors are asymptotic; inspect convergence and sparse factor levels.")
    y = st.selectbox("Outcome", numeric, key="qreg_y")
    predictors = st.multiselect("Predictors", [c for c in all_cols if c != y], key="qreg_x")
    q = st.slider("Target quantile", 0.05, 0.95, 0.50, 0.05, key="qreg_q")
    if st.button("Fit quantile regression", type="primary", key="qreg_fit"):
        try:
            model, used = fit_quantile_regression(df, y, predictors, q)
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
