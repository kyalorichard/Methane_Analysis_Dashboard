import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from analysis_engine.ui import header, metric_row, render_sidebar_navigation, empty_state
from analysis_engine.advanced_research import (
    fit_spline_additive, fit_random_intercept_model, animal_trajectory_slopes,
    multivariate_trait_associations, regression_prediction_diagnostics,
    variance_components_mixedlm,
)
from platform_core.auth import require_principal

st.set_page_config(page_title="Advanced research analytics | Methane Phenotype Analytics", page_icon="🧬", layout="wide")
require_principal()
render_sidebar_navigation()
header("Advanced research analytics", "Spline-additive modelling, hierarchical variance decomposition, longitudinal trajectories and multi-trait association analysis.", badge="ADVANCED RESEARCH 5.0")

df = st.session_state.get("data")
if df is None or df.empty:
    empty_state("No active dataset", "Load a study dataset from the project workspace to use advanced research analytics.")
    st.stop()

numeric = df.select_dtypes(include="number").columns.tolist()
all_cols = df.columns.tolist()
roles = st.session_state.get("roles", {})
animal_default = roles.get("animal_id") if roles.get("animal_id") in all_cols else all_cols[0]
outcome_default = roles.get("methane") if roles.get("methane") in numeric else (numeric[0] if numeric else None)
metric_row([("RECORDS", f"{len(df):,}", "Rows in active dataset"), ("ANIMALS", f"{df[animal_default].nunique():,}", "Unique selected animal/group identifier"), ("NUMERIC TRAITS", f"{len(numeric):,}", "Numeric variables available")])

if not numeric:
    st.warning("No numeric variables are available for these analyses.")
    st.stop()

tabs = st.tabs(["Spline-additive model", "Mixed model & variance", "Longitudinal trajectories", "Multi-trait associations", "Prediction diagnostics"])

with tabs[0]:
    st.subheader("Nonlinear exposure–response modelling")
    st.caption("Fits a Gaussian regression with B-spline bases for selected continuous predictors and HC3 heteroskedasticity-robust covariance. It is not a penalised GAM.")
    y = st.selectbox("Outcome", numeric, index=numeric.index(outcome_default) if outcome_default in numeric else 0, key="ar_spline_y")
    smooth = st.multiselect("Smooth continuous predictors", [c for c in numeric if c != y], key="ar_spline_smooth")
    linear = st.multiselect("Additional linear/categorical predictors", [c for c in all_cols if c not in [y] + smooth], key="ar_spline_linear")
    k = st.slider("Spline basis degrees of freedom", 3, 8, 5, key="ar_spline_df")
    if st.button("Fit spline-additive model", type="primary", key="ar_fit_spline"):
        try:
            model, used = fit_spline_additive(df, y, smooth, linear, k)
            st.session_state["ar_spline_result"] = {"summary": model.summary().as_text(), "aic": model.aic, "bic": model.bic, "r2": model.rsquared, "n": len(used), "model": model}
        except Exception as exc:
            st.error(str(exc))
    result = st.session_state.get("ar_spline_result")
    if result:
        metric_row([("N", f"{result['n']:,}", "Complete observations"), ("R²", f"{result['r2']:.3f}", "In-sample fit; not predictive validation"), ("AIC", f"{result['aic']:.1f}", "Compare only models fitted to same response and data"), ("BIC", f"{result['bic']:.1f}", "Lower is preferred among comparable models")])
        st.code(result["summary"])
        st.download_button("Download model summary", result["summary"], "spline_additive_model_summary.txt", "text/plain")

with tabs[1]:
    st.subheader("Hierarchical model and variance decomposition")
    st.caption("Use an animal random intercept for repeated animal records, or herd/site as the grouping factor when the design supports it.")
    y = st.selectbox("Outcome", numeric, index=numeric.index(outcome_default) if outcome_default in numeric else 0, key="ar_mixed_y")
    group = st.selectbox("Random-intercept grouping variable", all_cols, index=all_cols.index(animal_default), key="ar_mixed_group")
    predictors = st.multiselect("Fixed-effect predictors", [c for c in all_cols if c not in [y, group]], key="ar_mixed_x")
    reml = st.checkbox("Use REML estimation", value=True, help="Use ML rather than REML when comparing models with different fixed-effect structures.")
    if st.button("Fit random-intercept mixed model", type="primary", key="ar_fit_mixed"):
        try:
            model, used = fit_random_intercept_model(df, y, predictors, group, reml)
            st.session_state["ar_mixed_result"] = {"summary": model.summary().as_text(), "variance": variance_components_mixedlm(model), "n": len(used), "groups": used[group].nunique()}
        except Exception as exc:
            st.error(str(exc))
    result = st.session_state.get("ar_mixed_result")
    if result:
        metric_row([("N", f"{result['n']:,}", "Complete records"), ("GROUPS", f"{result['groups']:,}", "Independent grouping levels")])
        st.dataframe(result["variance"], use_container_width=True, hide_index=True)
        st.code(result["summary"])
        st.download_button("Download variance components", result["variance"].to_csv(index=False).encode(), "variance_components.csv", "text/csv")

with tabs[2]:
    st.subheader("Within-animal phenotype trajectories")
    st.caption("Time must be numeric or ordinally encoded. Per-animal slopes are descriptive summaries, not a substitute for a population-level longitudinal model.")
    animal = st.selectbox("Animal identifier", all_cols, index=all_cols.index(animal_default), key="ar_traj_animal")
    time_col = st.selectbox("Time variable", numeric, key="ar_traj_time")
    y = st.selectbox("Phenotype", numeric, index=numeric.index(outcome_default) if outcome_default in numeric else 0, key="ar_traj_y")
    min_points = st.slider("Minimum observations per animal", 3, 10, 3, key="ar_traj_min")
    if st.button("Estimate animal-level trajectories", type="primary", key="ar_fit_traj"):
        try:
            result = animal_trajectory_slopes(df, animal, time_col, y, min_points)
            st.session_state["ar_trajectory_result"] = result
        except Exception as exc:
            st.error(str(exc))
    traj = st.session_state.get("ar_trajectory_result")
    if traj is not None:
        metric_row([("ANIMALS", f"{len(traj):,}", "Animals meeting repeated-record threshold"), ("MEDIAN SLOPE", f"{traj['slope_per_time_unit'].median():.4g}", "Phenotype units per time unit"), ("POSITIVE SLOPE", f"{(traj['slope_per_time_unit'] > 0).mean()*100:.1f}%", "Proportion with positive estimated slopes")])
        fig = px.histogram(traj, x="slope_per_time_unit", nbins=30, title="Distribution of animal-level phenotype slopes")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(traj, use_container_width=True, hide_index=True)
        st.download_button("Download animal trajectories", traj.to_csv(index=False).encode(), "animal_trajectory_slopes.csv", "text/csv")

with tabs[3]:
    st.subheader("Multi-trait association analysis")
    traits = st.multiselect("Select numeric traits", numeric, default=numeric[:min(6, len(numeric))], key="ar_traits")
    method = st.radio("Correlation estimator", ["spearman", "pearson"], horizontal=True, key="ar_trait_method")
    if st.button("Calculate trait associations", type="primary", key="ar_trait_run"):
        try:
            st.session_state["ar_trait_result"] = multivariate_trait_associations(df, traits, method)
        except Exception as exc:
            st.error(str(exc))
    assoc = st.session_state.get("ar_trait_result")
    if assoc is not None:
        st.dataframe(assoc.sort_values("p_fdr_bh"), use_container_width=True, hide_index=True)
        st.download_button("Download trait associations", assoc.to_csv(index=False).encode(), "multitrait_associations.csv", "text/csv")
        st.caption("Pairwise complete observations are used. P-values are adjusted across the tested trait pairs using Benjamini–Hochberg FDR.")

with tabs[4]:
    st.subheader("Held-out prediction calibration and residual diagnostics")
    st.caption("Supply genuinely held-out or out-of-fold predictions. Do not use fitted training predictions to claim predictive validity.")
    obs = st.selectbox("Observed outcome column", numeric, key="ar_pred_obs")
    pred = st.selectbox("Predicted outcome column", [c for c in numeric if c != obs], key="ar_pred_pred") if len(numeric) > 1 else None
    if pred:
        if st.button("Calculate prediction diagnostics", type="primary", key="ar_pred_run"):
            try:
                st.session_state["ar_prediction_diagnostics"] = regression_prediction_diagnostics(df[obs], df[pred])
            except Exception as exc:
                st.error(str(exc))
        diag = st.session_state.get("ar_prediction_diagnostics")
        if diag:
            st.json(diag)
            paired = pd.DataFrame({"observed": pd.to_numeric(df[obs], errors="coerce"), "predicted": pd.to_numeric(df[pred], errors="coerce")}).dropna()
            fig = px.scatter(paired, x="predicted", y="observed", title="Observed versus predicted values")
            lo = min(paired.min()); hi = max(paired.max())
            fig.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi, line=dict(dash="dash"))
            st.plotly_chart(fig, use_container_width=True)
            st.caption(diag["note"])
