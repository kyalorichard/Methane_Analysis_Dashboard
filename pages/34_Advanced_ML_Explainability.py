import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_val_predict
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, brier_score_loss
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LinearRegression
from analysis_engine.settings_config import load_active_settings
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
from analysis_engine.ml import REGRESSORS
from analysis_engine.research_methods import grouped_learning_curve, feature_selection_stability, external_regression_validation
from analysis_engine.research_hardening import CLASSIFIERS
from analysis_engine.service_registry import get_service

render_sidebar_navigation()
header("Unified Research Model Lab", "Integrated workflows for regression prediction, phenotype classification, model validation, explainability and independent-cohort assessment.")
from analysis_engine.ui import render_workflow_shortcuts
render_workflow_shortcuts("Model Lab workflows", [
    ("Regression benchmarking", "pages/04_ML_Benchmarking.py", "📈"),
    ("Classification & mixed models", "pages/25_Research_Model_Lab.py", "🧬"),
    ("Variable importance", "pages/09_Explainability.py", "🔎"),
])
st.divider()
cfg=load_active_settings(st.session_state); comparison_cfg=cfg.get("comparison", {})
df=get_data(); roles=get_roles(df); nums=numeric_cols(df)
if len(df)<10:
    st.warning("Load a dataset with sufficient observations before running advanced ML workflows.")
    st.stop()

st.info("All internal validation workflows keep animal records together. If animals are clustered within herds, farms or sites, use the highest independent sampling unit as the grouping variable. These analyses are predictive, not causal.")

# Keep analytical controls in the page body, not in the global navigation sidebar.
with st.container(border=True):
    st.markdown("#### Analysis configuration")
    st.caption("Choose the target, independent grouping unit and predictors before running the validation workflows below.")
    cfg_a, cfg_b, cfg_c = st.columns([1.1, 1.1, 1.0])
    with cfg_a:
        outcome=choose_col(df,"Continuous target",roles.get("methane"),nums)
    with cfg_b:
        group_default=comparison_cfg.get("group_column") if comparison_cfg.get("group_column") in df.columns else roles.get("animal_id")
        animal=choose_col(df,"Grouping unit",group_default)
    with cfg_c:
        seed=st.number_input("Random seed",min_value=0,max_value=999999,value=int(comparison_cfg.get("random_state",42)))
    features=st.multiselect("Predictor variables",[c for c in df.columns if c not in [outcome,animal]],default=[c for c in nums if c!=outcome][:8],help="Select variables available at the intended prediction time. Exclude target-derived or post-outcome variables.")

if not features:
    st.warning("Select at least one predictor to continue.")
    st.stop()

numeric=[c for c in features if pd.api.types.is_numeric_dtype(df[c])]
categorical=[c for c in features if c not in numeric]
prep=ColumnTransformer([("num",Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler())]),numeric),
                        ("cat",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore"))]),categorical)])

# Create a consistent analysis frame and pipeline factory.
d=df[[outcome,animal]+features].copy(); d[outcome]=pd.to_numeric(d[outcome],errors="coerce"); d=d.dropna(subset=[outcome,animal])
X=d[features]; y=d[outcome].astype(float); groups=d[animal].astype(str)
if groups.nunique()<5:
    st.error("At least five independent groups are required for this advanced validation workspace.")
    st.stop()

st.subheader("Research workflows")
st.caption("Choose a workflow based on the research question. The dataset, target, predictors and grouping unit configured above are shared across all three workflows.")
regression_tab, classification_tab, validation_tab = st.tabs(["1 · Regression & phenotype prediction", "2 · Classification & phenotype identification", "3 · Model validation & interpretation"])

with regression_tab:
    st.subheader("1. Grouped learning curves")
    curve_model=st.selectbox("Learning-curve estimator",list(REGRESSORS),index=list(REGRESSORS).index("Extra Trees") if "Extra Trees" in REGRESSORS else 0)
    curve_folds=st.slider("Grouped folds",2,8,int(comparison_cfg.get("n_splits",5)),key="r62_curve_folds")
    if st.button("Calculate grouped learning curve",key="r62_curve_run"):
        try:
            pipe=Pipeline([("prep",clone(prep)),("model",clone(REGRESSORS[curve_model]))])
            result=grouped_learning_curve(pipe,X,y,groups,cv_splits=curve_folds)
            st.session_state["r62_learning_curve"]=result
        except Exception as e: st.error(str(e))
    if "r62_learning_curve" in st.session_state:
        q=st.session_state["r62_learning_curve"]
        st.dataframe(q,use_container_width=True,hide_index=True)
        fig=px.line(q,x="training_examples",y=["train_rmse_mean","validation_rmse_mean"],markers=True,title="Training and grouped-validation RMSE")
        fig.update_yaxes(title="RMSE (lower is better)"); st.plotly_chart(fig,use_container_width=True)
        st.download_button("Download learning-curve data",q.to_csv(index=False).encode(),"grouped_learning_curve.csv")
    st.caption("Training sizes are record counts selected within GroupKFold splits; group counts and fold composition should be reviewed for highly unequal cluster sizes.")

with validation_tab:
    st.divider(); st.subheader("2. Feature-selection stability")
    st.caption("Group-bootstrap selection frequency using tree-based impurity importance. This is a stability screen, not a causal ranking; correlated predictors can exchange importance.")
    stability_model=st.selectbox("Tree estimator",["Random Forest","Extra Trees"],key="r62_stability_model")
    stability_resamples=st.slider("Group bootstrap resamples",20,200,50,key="r62_stability_n")
    stability_topk=st.slider("Features selected per resample",1,len(features),min(5,len(features)),key="r62_topk")
    if st.button("Estimate feature-selection stability",key="r62_stability_run"):
        if not numeric or len(numeric)!=len(features): st.error("For this release, stability selection requires numeric predictors only. Encode categorical variables using a prespecified, reproducible scheme before analysis.")
        else:
            try:
                from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
                estimator=RandomForestRegressor(n_estimators=180,min_samples_leaf=2,n_jobs=-1,random_state=int(seed)) if stability_model=="Random Forest" else ExtraTreesRegressor(n_estimators=180,min_samples_leaf=2,n_jobs=-1,random_state=int(seed))
                out=feature_selection_stability(X,y,estimator,groups,n_resamples=stability_resamples,top_k=stability_topk,random_state=int(seed))
                st.session_state["r62_stability"]=out
            except Exception as e: st.error(str(e))
    if "r62_stability" in st.session_state:
        q=st.session_state["r62_stability"]; st.dataframe(q,use_container_width=True,hide_index=True)
        st.plotly_chart(px.bar(q.sort_values("selection_frequency"),x="selection_frequency",y="feature",orientation="h",title="Frequency of selection across group bootstraps"),use_container_width=True)
        st.download_button("Download stability results",q.to_csv(index=False).encode(),"feature_selection_stability.csv")

with validation_tab:
    st.divider(); st.subheader("3. SHAP explainability")
    st.caption("SHAP is computed on a sampled held-out set using the complete preprocessing-and-model pipeline. Kernel-based explanations can be computationally expensive; results depend on the background sample.")
    shap_model=st.selectbox("Model to explain",list(REGRESSORS),index=list(REGRESSORS).index("Extra Trees") if "Extra Trees" in REGRESSORS else 0,key="r62_shap_model")
    shap_background=st.slider("Background sample size",10,60,25,key="r62_shap_bg")
    shap_rows=st.slider("Rows to explain",10,100,40,key="r62_shap_rows")
    if st.button("Run SHAP analysis",key="r62_shap_run"):
        try:
            import shap
            split=GroupShuffleSplit(n_splits=1,test_size=.25,random_state=int(seed)); tr,te=next(split.split(X,y,groups))
            pipe=Pipeline([("prep",clone(prep)),("model",clone(REGRESSORS[shap_model]))]); pipe.fit(X.iloc[tr],y.iloc[tr])
            bg=X.iloc[tr].sample(min(shap_background,len(tr)),random_state=int(seed)); explain=X.iloc[te].sample(min(shap_rows,len(te)),random_state=int(seed))
            explainer=shap.Explainer(pipe.predict,bg); sv=explainer(explain)
            vals=np.asarray(sv.values)
            if vals.ndim==3: vals=vals[:,:,0]
            imp=pd.DataFrame({"feature":features,"mean_absolute_shap":np.abs(vals).mean(axis=0)}).sort_values("mean_absolute_shap",ascending=False)
            st.session_state["r62_shap_summary"]=imp; st.session_state["r62_shap_values"]=pd.DataFrame(vals,columns=features)
            st.session_state["r62_shap_meta"]={"model":shap_model,"n_explained":len(explain),"n_background":len(bg),"heldout_groups":int(groups.iloc[te].nunique())}
        except ImportError: st.error("SHAP is not installed. Install the optional dependency with: python -m pip install shap")
        except Exception as e: st.error(f"SHAP analysis failed: {type(e).__name__}: {e}")
    if "r62_shap_summary" in st.session_state:
        meta=st.session_state["r62_shap_meta"]; st.caption(f"{meta['model']} · {meta['n_explained']} explained records · {meta['n_background']} background records · {meta['heldout_groups']} held-out groups")
        q=st.session_state["r62_shap_summary"]; st.dataframe(q,use_container_width=True,hide_index=True)
        st.plotly_chart(px.bar(q.sort_values("mean_absolute_shap"),x="mean_absolute_shap",y="feature",orientation="h",title="Mean absolute SHAP value"),use_container_width=True)
        st.download_button("Download SHAP summary",q.to_csv(index=False).encode(),"shap_global_importance.csv")

with regression_tab:
    st.divider(); st.subheader("4. Prediction uncertainty — group-split conformal intervals")
    st.caption("Split-conformal prediction intervals use a group-disjoint calibration subset. Under exchangeability of independent groups, marginal coverage is targeted; distribution shift or clustered dependence above the selected group level can invalidate this guarantee.")
    conf_model=st.selectbox("Conformal regression model",list(REGRESSORS),index=list(REGRESSORS).index("Extra Trees") if "Extra Trees" in REGRESSORS else 0,key="r62_conf_model")
    coverage=st.select_slider("Target marginal coverage",options=[0.80,0.85,0.90,0.95],value=0.90,key="r62_coverage")
    if st.button("Estimate group-split conformal intervals",key="r62_conf_run"):
        try:
            gss=GroupShuffleSplit(n_splits=1,test_size=.35,random_state=int(seed)); fit_idx,hold_idx=next(gss.split(X,y,groups))
            gss2=GroupShuffleSplit(n_splits=1,test_size=.5,random_state=int(seed)+1); cal_rel,test_rel=next(gss2.split(X.iloc[hold_idx],y.iloc[hold_idx],groups.iloc[hold_idx]))
            cal_idx=hold_idx[cal_rel]; test_idx=hold_idx[test_rel]
            model=Pipeline([("prep",clone(prep)),("model",clone(REGRESSORS[conf_model]))]); model.fit(X.iloc[fit_idx],y.iloc[fit_idx])
            cal_err=np.abs(y.iloc[cal_idx].to_numpy()-model.predict(X.iloc[cal_idx])); n=len(cal_err)
            rank=min(n,int(np.ceil((n+1)*coverage)))
            radius=float(np.sort(cal_err)[rank-1]) if n else np.nan
            pred=model.predict(X.iloc[test_idx]); obs=y.iloc[test_idx].to_numpy()
            res=pd.DataFrame({"observed":obs,"predicted":pred,"lower":pred-radius,"upper":pred+radius,"absolute_error":np.abs(obs-pred)})
            summary={"model":conf_model,"target_coverage":coverage,"calibration_groups":int(groups.iloc[cal_idx].nunique()),"test_groups":int(groups.iloc[test_idx].nunique()),"calibration_n":n,"interval_radius":radius,"test_empirical_coverage":float(((obs>=pred-radius)&(obs<=pred+radius)).mean()),"test_mean_width":float(2*radius)}
            st.session_state["r62_conformal"]=(summary,res)
        except Exception as e: st.error(str(e))
    if "r62_conformal" in st.session_state:
        summary,res=st.session_state["r62_conformal"]; st.json(summary); st.dataframe(res,use_container_width=True,hide_index=True)
        st.download_button("Download prediction intervals",res.to_csv(index=False).encode(),"group_split_conformal_intervals.csv")

with validation_tab:
    st.divider(); st.subheader("5. Conventional statistics versus machine learning")
    st.caption("Run the dedicated comparison workspace to evaluate conventional statistical models and ML algorithms on matched animal-grouped folds.")
    st.page_link("pages/38_Conventional_vs_ML_Comparison.py", label="Open Conventional vs ML Comparison", icon="⚖️")

with regression_tab:
    st.divider(); st.subheader("6. Independent external validation")
    st.caption("Upload an independent cohort. The model is fitted only on the active development dataset and evaluated on the uploaded external dataset without refitting. Ensure identical variable definitions, units, instruments and outcome protocol.")
    ext_file=st.file_uploader("External validation dataset (CSV or Parquet)",type=["csv","parquet","pq"],key="r62_external_file")
    ext_model=st.selectbox("Frozen model",list(REGRESSORS),index=list(REGRESSORS).index("Extra Trees") if "Extra Trees" in REGRESSORS else 0,key="r62_external_model")
    if st.button("Fit development model and evaluate external cohort",key="r62_external_run",disabled=ext_file is None):
        try:
            ext=pd.read_csv(ext_file) if ext_file.name.lower().endswith(".csv") else pd.read_parquet(ext_file)
            required=[outcome]+features; missing=[c for c in required if c not in ext.columns]
            if missing: raise ValueError(f"External dataset is missing: {missing}")
            pipe=Pipeline([("prep",clone(prep)),("model",clone(REGRESSORS[ext_model]))]); pipe.fit(X,y)
            summary=external_regression_validation(pipe,ext,outcome,features)
            st.session_state["r62_external_result"]=(summary,ext_file.name,ext_model)
        except Exception as e: st.error(f"External validation failed: {e}")
    if "r62_external_result" in st.session_state:
        summary,filename,model_name=st.session_state["r62_external_result"]; st.caption(f"External source: {filename} · Frozen model: {model_name}"); st.json(summary)

with classification_tab:
    st.divider(); st.subheader("7. Classification benchmarking and calibration")
    st.caption("Classification uses stratified animal-grouped folds. Use nested grouped classification below when tuning and probability calibration are required within each outer training fold.")
    class_target=st.selectbox("Categorical target",[c for c in df.columns if c not in features+[animal] and df[c].nunique(dropna=True)>=2],key="r62_class_target") if any(c for c in df.columns if c not in features+[animal] and df[c].nunique(dropna=True)>=2) else None
    if class_target:
        class_models=st.multiselect("Classifiers",list(CLASSIFIERS),default=list(CLASSIFIERS),key="r62_class_models")
        if st.button("Run animal-grouped classification benchmark",key="r62_class_run",disabled=not class_models):
            try:
                scores,matrices,labels=get_service("grouped_classification")(df,class_target,features,animal,selected_models=class_models,n_splits=5,seed=int(seed))
                st.session_state["r62_classification"]=(scores,matrices,labels)
            except Exception as e: st.error(str(e))
        if "r62_classification" in st.session_state:
            scores,matrices,labels=st.session_state["r62_classification"]; st.dataframe(scores,use_container_width=True,hide_index=True)
            st.download_button("Download classification metrics",scores.to_csv(index=False).encode(),"grouped_classification_benchmark.csv")
            for name,matrix in matrices.items():
                st.markdown(f"**{name} — confusion matrix**"); st.dataframe(matrix,use_container_width=True)
    else: st.info("No eligible categorical target with at least two observed classes was found outside the selected predictors and grouping variable.")

    st.warning("Interpretation limits: SHAP and feature importance describe model reliance, not causal effects. Conformal coverage depends on exchangeability at the independent-group level. External validation requires a genuinely independent cohort and harmonised measurement protocol.")

with classification_tab:
    st.divider(); st.subheader("8. Nested grouped classification and probability calibration")
    st.caption("Nested stratified group CV evaluates each animal only in an outer test fold. Hyperparameter tuning and probability calibration use only the corresponding outer training groups. Use the highest independent sampling unit (e.g. herd or farm) when animals are clustered within it.")
    from analysis_engine.classification_validation import grouped_nested_classification, CLASSIFICATION_GRIDS, _pipeline
    class_target_nested=st.selectbox("Classification outcome",[c for c in df.columns if c not in features+[animal] and df[c].nunique(dropna=True)>=2],key="r63_nested_class_target") if any(c for c in df.columns if c not in features+[animal] and df[c].nunique(dropna=True)>=2) else None
    if class_target_nested:
        nested_models=st.multiselect("Models for nested grouped classification",list(CLASSIFICATION_GRIDS),default=["Logistic Regression","Random Forest","Extra Trees"],key="r63_nested_models")
        cal_method=st.selectbox("Probability calibration",["sigmoid","none"],format_func=lambda x:"Group-cross-fitted sigmoid calibration" if x=="sigmoid" else "Uncalibrated probabilities",key="r63_cal_method")
        tune_class=st.checkbox("Tune hyperparameters inside outer training folds",value=True,key="r63_tune_class")
        if st.button("Run nested grouped classification",key="r63_nested_run",disabled=not nested_models):
            try:
                scores,results,labels=grouped_nested_classification(df,class_target_nested,features,animal,
                    models=nested_models,outer_splits=5,inner_splits=3,calibration=cal_method,
                    random_state=int(seed),tune=tune_class)
                st.session_state["r63_nested_classification"]=(scores,results,labels,class_target_nested)
            except Exception as e: st.error(f"Nested classification failed: {e}")
        if "r63_nested_classification" in st.session_state:
            scores,results,labels,target_saved=st.session_state["r63_nested_classification"]
            if target_saved==class_target_nested:
                st.dataframe(scores,use_container_width=True,hide_index=True)
                st.download_button("Download nested classification metrics",scores.to_csv(index=False).encode(),"nested_grouped_classification_metrics.csv")
                for model_name,result in results.items():
                    with st.expander(f"{model_name} — out-of-fold diagnostics"):
                        st.dataframe(result["confusion_matrix"],use_container_width=True)
                        st.dataframe(result["probabilities"],use_container_width=True,hide_index=True)
                        st.download_button(f"Download {model_name} OOF probabilities",result["probabilities"].to_csv(index=False).encode(),f"{model_name.lower().replace(' ','_')}_oof_probabilities.csv")
                        st.json({"metrics":result["summary"],"folds":result["folds"]})
    else:
        st.info("No eligible categorical outcome was found for nested classification.")

    st.warning("Classification validation: nested group-aware probability calibration and multiclass OOF probability metrics are now available. Remaining limitations include calibration method comparisons (e.g. isotonic), threshold optimisation with prespecified utility, decision-curve analysis, classification-specific SHAP, and independent external classification workflow integration. Calibration is not a substitute for external validation.")

with classification_tab:
    st.divider(); st.subheader("9. Independent external classification validation")
    st.caption("Fit a classifier on the active development cohort, freeze it, and evaluate an independent uploaded cohort without refitting. The external outcome must use the same class labels and definitions.")
    ext_class_file=st.file_uploader("External classification cohort (CSV or Parquet)",type=["csv","parquet","pq"],key="r63_external_class_file")
    ext_class_model=st.selectbox("Development classifier",list(CLASSIFICATION_GRIDS),key="r63_external_class_model")
    if st.button("Fit and freeze development classifier; validate externally",key="r63_external_class_run",disabled=ext_class_file is None or class_target_nested is None):
        try:
            from analysis_engine.classification_validation import external_classification_validation
            extc=pd.read_csv(ext_class_file) if ext_class_file.name.lower().endswith(".csv") else pd.read_parquet(ext_class_file)
            needed=[class_target_nested]+features
            missing=[c for c in needed if c not in extc.columns]
            if missing: raise ValueError(f"External dataset is missing: {missing}")
            dev=df[[class_target_nested]+features].dropna(subset=[class_target_nested]).copy()
            model=_pipeline(dev,features,CLASSIFICATION_GRIDS[ext_class_model][0])
            model.fit(dev[features],dev[class_target_nested].astype(str))
            ext_summary=external_classification_validation(model,extc,class_target_nested,features)
            st.session_state["r63_external_class_result"]=(ext_summary,ext_class_file.name,ext_class_model)
        except Exception as e: st.error(f"External classification validation failed: {e}")
    if "r63_external_class_result" in st.session_state:
        ext_summary,ext_name,ext_model_name=st.session_state["r63_external_class_result"]
        st.caption(f"External cohort: {ext_name} · Frozen classifier: {ext_model_name}")
        st.json(ext_summary)

with validation_tab:
    st.divider(); st.subheader("10. External cohort transportability audit")
    st.caption("Screen schema and identifier overlap, then quantify predictor distribution differences. These checks do not prove independence or measurement equivalence; review cohort provenance and protocol metadata separately.")
    transport_file=st.file_uploader("Upload external cohort for transportability audit (CSV or Parquet)",type=["csv","parquet","pq"],key="r64_transport_file")
    if transport_file is not None:
        try:
            ext_transport=pd.read_csv(transport_file) if transport_file.name.lower().endswith(".csv") else pd.read_parquet(transport_file)
            id_options=["(not supplied)"]+list(df.columns)
            animal_id_audit=st.selectbox("Animal identifier column",id_options,key="r64_animal_id")
            group_id_audit=st.selectbox("Independent cluster identifier (farm/herd/site)",id_options,key="r64_group_id")
            cohort_id_audit=st.selectbox("Cohort identifier (if available)",id_options,key="r64_cohort_id")
            if st.button("Run external cohort audit and predictor shift",key="r64_audit_run"):
                from analysis_engine.transportability import audit_external_cohort, distribution_shift_report
                optional_id=lambda x: None if x=="(not supplied)" else x
                audit=audit_external_cohort(df,ext_transport,animal_id=optional_id(animal_id_audit),
                    group_id=optional_id(group_id_audit),cohort_id=optional_id(cohort_id_audit),required_columns=features)
                shift=distribution_shift_report(df,ext_transport,features)
                st.session_state["r64_transport_audit"]=(audit,shift,transport_file.name)
            if "r64_transport_audit" in st.session_state:
                audit,shift,source_name=st.session_state["r64_transport_audit"]
                st.caption(f"External source: {source_name}")
                st.metric("Identifier/schema screening", "Passed" if audit["independence_screen_passed"] else "Review required")
                st.json(audit)
                st.dataframe(shift,use_container_width=True,hide_index=True)
                st.download_button("Download predictor shift diagnostics",shift.to_csv(index=False).encode(),"external_predictor_shift.csv")
        except Exception as exc:
            st.error(f"External cohort audit failed: {exc}")

    st.info("The transportability utilities also provide cluster-bootstrap confidence intervals for regression performance and paired cluster-bootstrap comparisons of model predictions through `analysis_engine.transportability`. Supply predictions from the same held-out records and use the highest independent sampling unit. Negative candidate-minus-reference error differences favour the candidate model.")

# -----------------------------------------------------------------------------
# Versioned model registry: local, project-scoped metadata + safe skops artifacts.
# -----------------------------------------------------------------------------
with st.expander("Model registry — save, version, approve and reuse fitted models", expanded=False):
    st.caption("Register fitted scikit-learn pipelines as immutable versions. Artifacts use skops rather than pickle/joblib. Model metadata is scoped to the authenticated user and project; the registry can list that user's models across projects.")
    try:
        from platform_core.auth import require_principal
        principal = require_principal()
        registry_user = f"{principal.tenant_id}:{principal.subject}"
    except Exception:
        registry_user = str(st.session_state.get("user_id") or "local-user")
    registry_project = str(st.session_state.get("active_project_id") or st.session_state.get("analysis_project_scope") or "unassigned-project")
    registry_species = str(st.session_state.get("active_project_species") or st.session_state.get("analysis_species_scope") or "unspecified")

    try:
        from analysis_engine import model_registry as model_reg
        registered = model_reg.list_models(registry_user, include_all_projects=True)
    except Exception as registry_exc:
        registered = []
        st.error(f"Model registry could not be opened: {registry_exc}")

    st.markdown("#### Register or version a fitted model")
    reg_mode = st.radio("Registration action", ["Register a new model", "Create a new version of an existing model"], horizontal=True, key="r65_registry_mode")
    latest_lineages = {}
    for _item in registered:
        if _item["model_id"] not in latest_lineages or int(_item["version"]) > int(latest_lineages[_item["model_id"]]["version"]):
            latest_lineages[_item["model_id"]] = _item
    selected_lineage = None
    if reg_mode == "Create a new version of an existing model":
        if latest_lineages:
            lineage_options = {f"{m['model_name']} · {m['model_family']} · v{m['version']}": m for m in latest_lineages.values()}
            selected_lineage_label = st.selectbox("Model lineage to version", list(lineage_options), key="r65_registry_lineage")
            selected_lineage = lineage_options[selected_lineage_label]
        else:
            st.info("Register a model first before creating a new version.")
    st.warning("Registration refits the selected estimator on the complete active development cohort. This is a deployment/training fit, not a validation result. Validate with grouped cross-validation and/or an independent cohort before approving it.")
    reg_family = st.selectbox("Model task", ["Regression", "Classification"], key="r65_registry_family")
    if reg_family == "Regression":
        from analysis_engine.ml import REGRESSORS as registry_catalogue
        reg_target = outcome
        reg_models = list(registry_catalogue)
    else:
        from analysis_engine.research_hardening import CLASSIFIERS as registry_catalogue
        class_targets = [c for c in df.columns if c not in features + [animal] and df[c].nunique(dropna=True) >= 2]
        reg_target = st.selectbox("Classification outcome", class_targets, key="r65_registry_class_target") if class_targets else None
        reg_models = list(registry_catalogue)
    if reg_target is not None:
        reg_model_name = st.selectbox("Estimator to fit and register", reg_models, key="r65_registry_model")
        reg_display_name = st.text_input("Registry model name", value=f"{reg_model_name} · {reg_target}", key="r65_registry_name")
        reg_notes = st.text_area("Model notes / intended use", key="r65_registry_notes", placeholder="Record cohort, protocol, intended-use constraints and known limitations.")
        if st.button("Fit and register new model version", key="r65_registry_save"):
            try:
                from sklearn.base import clone
                from sklearn.compose import ColumnTransformer
                from sklearn.pipeline import Pipeline
                from sklearn.impute import SimpleImputer
                from sklearn.preprocessing import OneHotEncoder, StandardScaler
                from analysis_engine.data_provenance import dataframe_fingerprint
                from analysis_engine.model_registry import serialize_estimator, register_model_artifact
                reg_frame = df[[reg_target, animal] + features].copy().dropna(subset=[reg_target, animal])
                if reg_family == "Regression":
                    reg_frame[reg_target] = pd.to_numeric(reg_frame[reg_target], errors="coerce")
                    reg_frame = reg_frame.dropna(subset=[reg_target])
                    target_values = reg_frame[reg_target].astype(float)
                else:
                    target_values = reg_frame[reg_target].astype(str)
                    if target_values.nunique() < 2:
                        raise ValueError("Classification requires at least two observed outcome classes.")
                if reg_frame[animal].nunique() < 2:
                    raise ValueError("At least two independent groups are required to register a model.")
                reg_numeric = [c for c in features if pd.api.types.is_numeric_dtype(reg_frame[c])]
                reg_categorical = [c for c in features if c not in reg_numeric]
                reg_prep = ColumnTransformer([
                    ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), reg_numeric),
                    ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), reg_categorical),
                ])
                estimator = Pipeline([("prep", reg_prep), ("model", clone(registry_catalogue[reg_model_name]))])
                estimator.fit(reg_frame[features], target_values)
                payload = serialize_estimator(estimator)
                fingerprint = dataframe_fingerprint(reg_frame)
                if reg_mode == "Create a new version of an existing model":
                    if selected_lineage is None:
                        raise ValueError("Select an existing model lineage first.")
                    if (selected_lineage["task_type"] != reg_family.lower()
                            or selected_lineage["model_family"] != reg_model_name
                            or selected_lineage["outcome"] != reg_target
                            or selected_lineage["features"] != list(features)):
                        raise ValueError("To create a version, task, estimator, outcome and ordered predictor list must match the selected model lineage.")
                    from analysis_engine.model_registry import add_model_version
                    result = add_model_version(selected_lineage["model_id"], payload=payload,
                        user_scope=registry_user, validation_metrics={}, notes=reg_notes,
                        status="candidate", training_records=len(reg_frame),
                        training_groups=int(reg_frame[animal].nunique()), dataset_fingerprint=fingerprint)
                    st.success(f"Created version {result['version']} of {selected_lineage['model_name']} (candidate). Model ID: {result['model_id']}")
                else:
                    result = register_model_artifact(payload=payload, model_name=reg_display_name,
                        model_family=reg_model_name, task_type=reg_family.lower(), outcome=reg_target,
                        features=list(features), user_scope=registry_user, project_scope=registry_project,
                        species_scope=registry_species, group_column=animal, dataset_fingerprint=fingerprint,
                        training_records=len(reg_frame), training_groups=int(reg_frame[animal].nunique()),
                        random_seed=int(seed), validation_metrics={}, notes=reg_notes, status="candidate")
                    st.success(f"Registered {result['model_name']} as version {result['version']} (candidate). Model ID: {result['model_id']}")
                st.rerun()
            except Exception as exc:
                st.error(f"Model registration failed: {type(exc).__name__}: {exc}")
    else:
        st.info("No eligible classification outcome was found in the active dataset.")

    st.divider()
    st.markdown("#### Registered models and lifecycle")
    registered = model_reg.list_models(registry_user, include_all_projects=True)
    if registered:
        model_table = pd.DataFrame([{k: item.get(k) for k in ["model_name", "version", "model_family", "task_type", "outcome", "project_scope", "training_records", "training_groups", "status", "created_at"]} for item in registered])
        st.dataframe(model_table, use_container_width=True, hide_index=True)
        options = {f"{m['model_name']} · v{m['version']} · {m['status']} · {m['project_scope'][:8]}": m for m in registered}
        selected_label = st.selectbox("Select registered model version", list(options), key="r65_registry_selected")
        selected_record = options[selected_label]
        if selected_record["status"] != "approved":
            st.caption("Approval is an explicit governance decision. Approve only after reviewing grouped validation and, where appropriate, independent external validation.")
            attest = st.checkbox("I have reviewed the validation evidence and accept the model's documented intended-use limitations.", key="r65_registry_attest")
            if st.button("Approve selected model version", key="r65_registry_approve", disabled=not attest):
                try:
                    model_reg.set_model_status(selected_record["model_id"], selected_record["version"], registry_user, "approved")
                    st.success("Model version approved."); st.rerun()
                except Exception as exc: st.error(f"Approval failed: {exc}")
        else:
            if st.button("Retire selected model version", key="r65_registry_retire"):
                try:
                    model_reg.set_model_status(selected_record["model_id"], selected_record["version"], registry_user, "retired")
                    st.success("Model version retired."); st.rerun()
                except Exception as exc: st.error(f"Retirement failed: {exc}")
        try:
            record, artifact_payload = model_reg.read_model_artifact(selected_record["model_id"], selected_record["version"], registry_user)
            st.download_button("Download selected model artifact (.skops)", artifact_payload,
                file_name=f"{record['model_name']}_v{record['version']}.skops", mime="application/octet-stream", key="r65_registry_download")
            untrusted = model_reg.inspect_artifact(artifact_payload)
            if untrusted:
                st.warning("The artifact contains non-default Python types. Review the names below before loading: " + ", ".join(untrusted))
                trust_confirm = st.checkbox("I have reviewed and explicitly trust these artifact types.", key="r65_registry_trust")
            else:
                trust_confirm = True
            if selected_record["status"] == "approved":
                if st.button("Load approved model and predict active dataset", key="r65_registry_predict", disabled=not trust_confirm):
                    try:
                        loaded_record, loaded_model = model_reg.load_registered_model(
                            selected_record["model_id"], selected_record["version"], registry_user,
                            trusted_types=untrusted if trust_confirm else [])
                        missing_cols = [c for c in loaded_record["features"] if c not in df.columns]
                        if missing_cols:
                            raise ValueError(f"Active dataset is missing model predictors: {missing_cols}")
                        prediction = loaded_model.predict(df[loaded_record["features"]])
                        pred_frame = pd.DataFrame({"row_index": df.index, "prediction": prediction})
                        if loaded_record["task_type"] == "regression" and loaded_record["outcome"] in df.columns:
                            pred_frame.insert(1, "observed", pd.to_numeric(df[loaded_record["outcome"]], errors="coerce").to_numpy())
                        if loaded_record["task_type"] == "classification":
                            pred_frame["predicted_class"] = prediction.astype(str)
                            if hasattr(loaded_model, "predict_proba"):
                                probs = loaded_model.predict_proba(df[loaded_record["features"]])
                                for j, cls in enumerate(getattr(loaded_model, "classes_", [])):
                                    pred_frame[f"probability_{cls}"] = probs[:, j]
                        st.session_state["r65_registry_predictions"] = pred_frame
                        st.success(f"Generated predictions using approved model {loaded_record['model_name']} v{loaded_record['version']}.")
                    except Exception as exc: st.error(f"Model reuse failed: {type(exc).__name__}: {exc}")
            else:
                st.info("Only approved model versions can be loaded for prediction from the registry.")
        except Exception as exc:
            st.error(f"Artifact integrity or inspection check failed: {exc}")
        if "r65_registry_predictions" in st.session_state:
            st.dataframe(st.session_state["r65_registry_predictions"].head(100), use_container_width=True, hide_index=True)
            st.download_button("Download model predictions", st.session_state["r65_registry_predictions"].to_csv(index=False).encode(),
                "registered_model_predictions.csv", key="r65_registry_predictions_download")
    else:
        st.info("No models have been registered yet. Fit and register a model above to create the first version.")
    st.caption("Persistence note: this release stores registry metadata in the configured local SQLite database and .skops artifacts in MODEL_REGISTRY_DIR. On Streamlit Cloud or another ephemeral filesystem, configure persistent storage before relying on long-term retention. PostgreSQL/S3-backed model artifact storage is not yet wired into this registry.")
