import streamlit as st
import pandas as pd
import plotly.express as px

from analysis_engine.model_comparison import compare_grouped_models, ML_MODELS
from analysis_engine.settings_config import load_active_settings
from analysis_engine.ui import (
    header, render_sidebar_navigation, get_data, get_roles, numeric_cols, choose_col,
)

render_sidebar_navigation()
header(
    "Conventional vs Machine Learning Comparison",
    "Compare statistical and ML regression models using identical animal-grouped validation folds.",
    badge="MATCHED MODEL BENCHMARK",
)

cfg = load_active_settings(st.session_state)
comparison_cfg = cfg.get("comparison", {})
df = get_data()
if df is None or df.empty:
    st.info("Load a dataset in Project Workspace before running the comparison.")
    st.stop()

roles = get_roles(df)
nums = numeric_cols(df)
if not nums:
    st.error("No numeric outcome variable is available in the active dataset.")
    st.stop()

with st.container(border=True):
    st.subheader("1. Analysis design")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        outcome = choose_col(df, "Continuous methane outcome", roles.get("methane"), nums)
    with col_b:
        group_default = comparison_cfg.get("group_column")
        if group_default not in df.columns:
            group_default = roles.get("animal_id")
        grouping_unit = choose_col(
            df, "Independent grouping unit", group_default,
            options=[c for c in df.columns if c != outcome],
        )
    with col_c:
        seed = st.number_input(
            "Random seed", min_value=0, max_value=999999,
            value=int(comparison_cfg.get("random_state", 42)), step=1,
        )
    predictor_candidates = [c for c in df.columns if c not in (outcome, grouping_unit)]
    default_predictors = [c for c in numeric_cols(df) if c != outcome][:8]
    predictors = st.multiselect(
        "Predictors", predictor_candidates, default=default_predictors,
        help="Use variables available at the intended prediction time. Exclude target-derived or post-outcome variables.",
    )

n_groups = int(df[grouping_unit].dropna().astype(str).nunique()) if grouping_unit in df.columns else 0
n_records = int(df[[outcome, grouping_unit]].dropna().shape[0]) if grouping_unit in df.columns else 0
m1, m2, m3 = st.columns(3)
m1.metric("Records with outcome and group", f"{n_records:,}")
m2.metric("Independent groups", f"{n_groups:,}")
m3.metric("Selected predictors", f"{len(predictors):,}")
if n_groups < 5:
    st.warning("At least five independent groups are required by this comparison engine. Consider whether a higher-level grouping unit is available.")

st.subheader("2. Select model families")
conventional_models = [
    "OLS (linear regression)",
    "GEE (exchangeable; marginal prediction)",
    "Mixed-effects model (random intercept; fixed-effect prediction)",
    "Spline regression (GAM-like)",
    "Quantile regression (median)",
    "Allometric power-law regression",
]
all_models = conventional_models + list(ML_MODELS)
family_col1, family_col2 = st.columns(2)
with family_col1:
    st.markdown("**Conventional statistical models**")
    selected_conventional = st.multiselect(
        "Statistical models", conventional_models,
        default=conventional_models[:5], key="cml_conventional_models",
    )
with family_col2:
    st.markdown("**Machine-learning models**")
    selected_ml = st.multiselect(
        "ML algorithms", list(ML_MODELS),
        default=[m for m in ("Random Forest", "Extra Trees", "SVR") if m in ML_MODELS],
        key="cml_ml_models",
    )
selected_models = selected_conventional + selected_ml

with st.expander("Validation and tuning settings", expanded=True):
    v1, v2, v3 = st.columns(3)
    with v1:
        folds = st.slider("Animal-grouped CV folds", 3, min(8, max(3, n_groups)),
                          min(int(comparison_cfg.get("n_splits", 5)), max(3, n_groups)),
                          key="cml_folds")
    with v2:
        bootstrap = st.select_slider(
            "Paired group-bootstrap replicates", options=[200, 500, 1000, 2000, 5000],
            value=int(comparison_cfg.get("n_boot", 500)), key="cml_bootstrap",
        )
    with v3:
        tune = st.checkbox("Tune ML hyperparameters inside each training fold",
                           value=bool(comparison_cfg.get("tune_models", False)), key="cml_tune")
    tuning_method = st.selectbox("Tuning strategy", ["random", "grid", "bayesian"],
                                 index=["random", "grid", "bayesian"].index(str(comparison_cfg.get("tuning_method", "random")))
                                 if str(comparison_cfg.get("tuning_method", "random")) in ["random", "grid", "bayesian"] else 0,
                                 disabled=not tune, key="cml_tuning_method")
    tuning_iter = st.slider("Tuning iterations (random/Bayesian)", 2, 40,
                            int(comparison_cfg.get("tuning_iter", 12)), disabled=not tune,
                            key="cml_tuning_iter")

st.info(
    "All selected models use the same GroupKFold partitions and predictor set. "
    "Imputation, encoding and scaling are estimated from each training fold. "
    "The grouping unit should be the highest independent sampling unit; use herd/farm/site "
    "rather than animal if animals are clustered within those units."
)

run_disabled = len(selected_models) < 2 or not predictors or n_groups < 5
if st.button("Run matched conventional-versus-ML comparison", type="primary", disabled=run_disabled):
    try:
        with st.spinner("Fitting models on matched grouped folds. Mixed-effects models and tuning may take several minutes..."):
            result = compare_grouped_models(
                df, outcome, predictors, grouping_unit,
                selected_models=selected_models,
                n_splits=folds,
                n_boot=bootstrap,
                random_state=int(seed),
                model_parameters=cfg.get("models", {}),
                preprocessing=cfg.get("preprocessing", {}),
                tune_models=bool(tune),
                tuning_iter=int(tuning_iter),
                tuning_method=tuning_method,
                conventional_parameters=cfg.get("conventional", {}),
            )
        st.session_state["conventional_ml_comparison_result"] = result
        st.session_state["conventional_ml_comparison_config"] = {
            "outcome": outcome, "grouping_unit": grouping_unit,
            "predictors": predictors, "models": selected_models,
            "folds": folds, "bootstrap_replicates": bootstrap,
            "random_seed": int(seed), "tuned": bool(tune),
        }
    except Exception as exc:
        st.error(f"Model comparison failed: {type(exc).__name__}: {exc}")

result = st.session_state.get("conventional_ml_comparison_result")
if result is not None:
    saved_cfg = st.session_state.get("conventional_ml_comparison_config", {})
    st.divider()
    st.subheader("3. Matched out-of-fold performance")
    st.caption(
        f"Outcome: {saved_cfg.get('outcome')} · Grouping: {saved_cfg.get('grouping_unit')} · "
        f"Folds: {result['folds']} · Records: {result['n_records']:,} · "
        f"Groups: {result['n_groups']:,}"
    )
    metrics = result["metrics"].copy()
    st.dataframe(metrics, use_container_width=True, hide_index=True)
    completed = metrics.loc[metrics["status"].eq("completed")].copy()
    if not completed.empty:
        st.markdown("**RMSE by model family**")
        st.plotly_chart(
            px.bar(completed.sort_values("RMSE"), x="model", y="RMSE", color="model_family",
                   hover_data=["MAE", "R2", "mean_prediction_bias", "fit_predict_seconds"],
                   title="Matched grouped-CV RMSE (lower is better)"),
            use_container_width=True,
        )
        st.markdown("**MAE by model family**")
        st.plotly_chart(
            px.bar(completed.sort_values("MAE"), x="model", y="MAE", color="model_family",
                   title="Matched grouped-CV MAE (lower is better)"),
            use_container_width=True,
        )
    failed = metrics.loc[metrics["status"].ne("completed")]
    if not failed.empty:
        st.warning("Some models did not complete. Review the warnings column before interpreting the ranking.")
        st.dataframe(failed[["model", "folds_completed", "status", "warnings"]], use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("4. Paired group-bootstrap comparison")
    st.caption(
        "Difference is RMSE(model A) minus RMSE(model B). Negative values favour model A; "
        "positive values favour model B. Intervals resample independent groups, not individual rows."
    )
    paired = result["paired_comparisons"]
    if paired.empty:
        st.info("No pairwise comparisons were available because fewer than two models completed.")
    else:
        st.dataframe(paired, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("5. Observed versus out-of-fold predicted values")
    oof = result["oof_predictions"]
    prediction_columns = [c for c in oof.columns if c.startswith("pred__")]
    if prediction_columns:
        selected_prediction = st.selectbox(
            "Model prediction to inspect", prediction_columns,
            format_func=lambda value: value.replace("pred__", ""), key="cml_oof_model",
        )
        plot_df = oof[["observed", selected_prediction]].rename(columns={selected_prediction: "predicted"})
        st.plotly_chart(
            px.scatter(plot_df, x="observed", y="predicted", opacity=0.65,
                       title=f"Observed vs predicted: {selected_prediction.replace('pred__', '')}"),
            use_container_width=True,
        )
        plot_df["residual"] = plot_df["observed"] - plot_df["predicted"]
        st.plotly_chart(
            px.scatter(plot_df, x="predicted", y="residual", opacity=0.65,
                       title="Residuals versus out-of-fold predictions"),
            use_container_width=True,
        )

    st.divider()
    st.subheader("6. Export results")
    st.download_button("Download model performance metrics", metrics.to_csv(index=False).encode("utf-8"),
                       "conventional_vs_ml_metrics.csv", "text/csv")
    st.download_button("Download paired RMSE comparisons", paired.to_csv(index=False).encode("utf-8"),
                       "paired_group_bootstrap_rmse.csv", "text/csv")
    st.download_button("Download out-of-fold predictions", oof.to_csv(index=False).encode("utf-8"),
                       "conventional_vs_ml_oof_predictions.csv", "text/csv")
    st.info(result["interpretation"])
    st.warning(
        "Interpretation: predictive performance does not establish causal validity or replace "
        "model-specific inference. OLS, GEE and mixed-effects models target different estimands; "
        "their predictive scores can be compared, but their coefficients and inferential claims "
        "should not be treated as interchangeable."
    )
