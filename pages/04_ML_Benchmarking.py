import streamlit as st
import plotly.express as px
from analysis_engine.ui import *
from analysis_engine.ml import grouped_regression_benchmark, REGRESSORS

from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header("Machine-learning benchmarking",
       "Select the algorithms to evaluate, or use the full model suite. Validation keeps all records from each animal in the same fold.")

df=get_data()
nums=numeric_cols(df)
roles=get_roles(df)
outcome=choose_col(df,"Continuous target",roles.get("methane"),nums)
animal=choose_col(df,"Animal ID",roles.get("animal_id"))
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

folds=st.slider("Animal-grouped cross-validation folds",3,10,5)
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
