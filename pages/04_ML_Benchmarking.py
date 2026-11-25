import streamlit as st
import plotly.express as px
from analysis_engine.ui import *
from analysis_engine.ml import grouped_regression_benchmark, nested_grouped_regression_benchmark, REGRESSORS
from analysis_engine.settings_config import load_active_settings

from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()
_cfg = load_active_settings(st.session_state)
_ml_cfg = _cfg.get("comparison", {})

header("Machine-learning benchmarking",
       "Select the algorithms to evaluate, or use the full model suite. Validation keeps all records from each animal in the same fold.")

df=get_data()
nums=numeric_cols(df)
roles=get_roles(df)
outcome=choose_col(df,"Continuous target",roles.get("methane"),nums)
animal_default = _ml_cfg.get("group_column") if _ml_cfg.get("group_column") in df.columns else roles.get("animal_id")
animal=choose_col(df,"Animal ID / independent grouping unit",animal_default)
features=st.multiselect("Predictor variables",
    [c for c in df.columns if c not in [outcome,animal]],
    default=[c for c in nums if c!=outcome][:6])

st.subheader("Model selection")
model_names=list(REGRESSORS.keys())
selection_mode=st.radio("How should models be selected?",
    ["Compare all available models","Select specific models"],
    horizontal=True,key="ml_selection_mode")
if selection_mode=="Compare all available models":
    selected_models=model_names
    st.caption(f"All {len(model_names)} available regression algorithms will be evaluated.")
else:
    selected_models=st.multiselect("Models to compare",model_names,
        default=model_names[:3],key="ml_selected_models",
        help="Choose one or more algorithms. Only selected models will be trained and scored.")
    st.caption(f"{len(selected_models)} of {len(model_names)} models selected.")

with st.expander("Available algorithms and model families"):
    st.markdown("""
    - **Regularised linear:** Ridge, Elastic Net
    - **Tree ensembles:** Random Forest, Extra Trees, HistGradientBoosting
    - **Kernel-based:** Support Vector Regression (SVR)
    - **Instance-based:** K-Nearest Neighbours (KNN)
    """)

folds=st.slider("Animal-grouped cross-validation folds",2,10,int(_ml_cfg.get("n_splits",5)))
run=st.button("Run selected model benchmark",type="primary",
              disabled=(not selected_models or not features))
if run:
    try:
        with st.spinner(f"Training and evaluating {len(selected_models)} model(s)..."):
            res=grouped_regression_benchmark(df,outcome,features,animal,folds,
                                             selected_models=selected_models)
        st.session_state["ml_benchmark_results"]=res
        st.session_state["ml_benchmark_selection"]=selected_models
    except Exception as e:
        st.error(str(e))

res=st.session_state.get("ml_benchmark_results")
if res is not None:
    st.subheader("Benchmark results")
    st.caption("Models evaluated: "+", ".join(st.session_state.get("ml_benchmark_selection",[])))
    st.dataframe(res,use_container_width=True)
    st.download_button("Download benchmark results",
        res.to_csv(index=False).encode("utf-8"),
        "grouped_ml_benchmark.csv","text/csv")
    valid=res.dropna(subset=["rmse_mean"]) if "rmse_mean" in res else res.iloc[0:0]
    if len(valid):
        st.plotly_chart(px.bar(valid.sort_values("rmse_mean"),x="model",
            y="rmse_mean",error_y="rmse_sd" if "rmse_sd" in valid else None,
            title="Grouped cross-validation RMSE (lower is better)"),
            use_container_width=True)
        st.plotly_chart(px.bar(valid.sort_values("mae_mean"),x="model",
            y="mae_mean",title="Grouped cross-validation MAE (lower is better)"),
            use_container_width=True)
st.info("All records from the same animal are assigned to the same validation fold. Preprocessing is fitted inside each fold. These are internal validation estimates, not external validation. Compare models using the same folds and predictor set.")


st.divider()
st.subheader("Nested animal-grouped validation")
st.caption("Optional, more computationally intensive evaluation. Hyperparameter selection occurs inside each outer training fold; the outer folds estimate generalisation performance.")
outer_folds=st.slider("Outer validation folds",3,8,5,key="nested_outer_folds")
inner_folds=st.slider("Inner tuning folds",2,5,3,key="nested_inner_folds")
nested_models=st.multiselect("Models for nested validation",model_names,
    default=[m for m in ["Ridge","Random Forest","Extra Trees"] if m in model_names],
    key="nested_model_selection")
if st.button("Run nested grouped benchmark",type="primary",disabled=(not nested_models or not features)):
    try:
        with st.spinner("Running nested grouped cross-validation. This may take several minutes."):
            nested=nested_grouped_regression_benchmark(df,outcome,features,animal,
                outer_splits=outer_folds,inner_splits=inner_folds,selected_models=nested_models)
        st.session_state["nested_ml_results"]=nested
    except Exception as exc:
        st.error(f"Nested benchmark failed: {exc}")
nested=st.session_state.get("nested_ml_results")
if nested is not None:
    st.dataframe(nested,use_container_width=True,hide_index=True)
    st.download_button("Download nested benchmark results",
        nested.to_csv(index=False).encode("utf-8"),"nested_grouped_ml_benchmark.csv","text/csv")
    st.warning("Interpret outer-fold estimates with their fold-level variability. Small numbers of animals, strong group imbalance and limited independent test groups can still produce uncertain performance estimates.")
