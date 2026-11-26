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
from analysis_engine.research_hardening import CLASSIFIERS, grouped_classification_benchmark

render_sidebar_navigation()
header("Advanced ML validation & explainable AI", "Grouped validation, model interpretation, calibration, uncertainty and independent-cohort assessment.")
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

st.divider(); st.subheader("5. Conventional statistics versus machine learning")
st.caption("Matched out-of-fold predictive comparison using identical GroupKFold partitions, predictors and independent grouping units. Conventional models include OLS, GEE, random-intercept mixed-effects, spline, median quantile and allometric regression; ML models include tree ensembles, boosting, SVR and KNN. This is predictive benchmarking, not a ranking of inferential validity or causal estimands.")
from analysis_engine.model_comparison import compare_grouped_models, ML_MODELS
comparison_catalogue=["OLS (linear regression)","GEE (exchangeable; marginal prediction)","Mixed-effects model (random intercept; fixed-effect prediction)","Spline regression (GAM-like)","Quantile regression (median)","Allometric power-law regression"]+list(ML_MODELS)
compare_models=st.multiselect("Models to compare",comparison_catalogue,default=["OLS (linear regression)","GEE (exchangeable; marginal prediction)","Mixed-effects model (random intercept; fixed-effect prediction)","Spline regression (GAM-like)","Quantile regression (median)","Random Forest","Extra Trees","SVR"],key="r64_compare_models")
_settings = load_active_settings(st.session_state)
_compare_cfg = _settings.get("comparison", {})
compare_folds=st.slider("Matched grouped CV folds",3,min(8,max(3,int(groups.nunique()))),min(int(_compare_cfg.get("n_splits",5)),max(3,int(groups.nunique()))),key="r64_compare_folds")
compare_boot=st.select_slider("Group-bootstrap replicates for paired RMSE differences",options=[200,500,1000,2000,5000],value=int(_compare_cfg.get("n_boot",500)),key="r64_compare_boot")
st.caption("Model hyperparameters are configured in Settings → Analysis & model settings. Changes are applied when you rerun this benchmark.")
if st.button("Run matched statistical-versus-ML benchmark",key="r64_compare_run",disabled=len(compare_models)<2):
    try:
        result=compare_grouped_models(df,outcome,features,animal,selected_models=compare_models,n_splits=compare_folds,n_boot=compare_boot,random_state=int(_compare_cfg.get("random_state",seed)),model_parameters=_settings.get("models",{}),preprocessing=_settings.get("preprocessing",{}),tune_models=bool(_compare_cfg.get("tune_models",False)),tuning_iter=int(_compare_cfg.get("tuning_iter",12)),tuning_method=str(_compare_cfg.get("tuning_method","random")),conventional_parameters=_settings.get("conventional",{}))
        st.session_state["r64_model_comparison"]=result
    except Exception as e: st.error(f"Model comparison failed: {type(e).__name__}: {e}")
if "r64_model_comparison" in st.session_state:
    result=st.session_state["r64_model_comparison"]
    st.markdown("**Out-of-fold predictive performance**")
    st.dataframe(result["metrics"],use_container_width=True,hide_index=True)
    valid=result["metrics"].query("status == 'completed'")
    if len(valid):
        st.plotly_chart(px.bar(valid.sort_values("RMSE"),x="model",y="RMSE",color="model_family",title="Matched grouped-CV RMSE (lower is better)"),use_container_width=True)
    st.markdown("**Paired group-bootstrap comparison of RMSE**")
    st.caption("Difference is RMSE(model A) minus RMSE(model B). Negative values favour A; positive values favour B. Confidence intervals are percentile intervals from resampling independent groups.")
    st.dataframe(result["paired_comparisons"],use_container_width=True,hide_index=True)
    st.markdown("**Out-of-fold predictions**")
    st.dataframe(result["oof_predictions"].head(500),use_container_width=True,hide_index=True)
    st.download_button("Download model metrics",result["metrics"].to_csv(index=False).encode(),"matched_model_comparison_metrics.csv")
    st.download_button("Download paired RMSE comparisons",result["paired_comparisons"].to_csv(index=False).encode(),"paired_group_bootstrap_rmse.csv")
    st.download_button("Download out-of-fold predictions",result["oof_predictions"].to_csv(index=False).encode(),"matched_model_oof_predictions.csv")
    st.info(result["interpretation"])
    st.divider()
    st.markdown("**Save this analysis as a reproducible experiment**")
    exp_name = st.text_input("Experiment name", value="Methane model comparison", key="r68_exp_name")
    exp_project = st.text_input("Project / study identifier", value=st.session_state.get("analysis_project_scope", "default-project"), key="r68_exp_project")
    exp_species = st.selectbox("Species", ["all", "cattle", "sheep", "goats", "other"], key="r68_exp_species")
    if st.button("Save experiment to registry", key="r68_save_experiment"):
        try:
            from analysis_engine.experiment_registry import save_experiment
            _uid = str(st.session_state.get("user_id") or st.session_state.get("username") or st.session_state.get("email") or "local-user")
            _cfg = {"settings": _settings, "outcome": outcome, "predictors": features, "grouping_unit": animal, "selected_models": compare_models, "folds": compare_folds, "bootstrap_replicates": compare_boot}
            import hashlib, sklearn
            _analysis_frame = df[[outcome, animal] + list(features)].copy()
            _fingerprint = hashlib.sha256(pd.util.hash_pandas_object(_analysis_frame, index=True).values.tobytes()).hexdigest()
            _meta = {"n_records": result["n_records"], "n_groups": result["n_groups"], "dataset_columns": list(df.columns), "dataset_fingerprint_sha256": _fingerprint, "scikit_learn_version": sklearn.__version__, "pandas_version": pd.__version__, "interpretation": result["interpretation"]}
            exp_id = save_experiment(_uid, exp_project.strip() or "default-project", exp_species, exp_name, _cfg, result["metrics"].to_dict("records"), result["paired_comparisons"].to_dict("records"), _meta)
            st.success(f"Experiment saved. Registry ID: {exp_id}")
        except Exception as exc: st.error(f"Could not save experiment: {type(exc).__name__}: {exc}")
    try:
        from analysis_engine.experiment_registry import list_experiments
        _uid = str(st.session_state.get("user_id") or st.session_state.get("username") or st.session_state.get("email") or "local-user")
        _saved = list_experiments(_uid, limit=20)
        if _saved:
            st.markdown("**Recent saved experiments**")
            st.dataframe(pd.DataFrame([{k:v for k,v in e.items() if k not in ("metrics","metadata")} for e in _saved]), use_container_width=True, hide_index=True)
    except Exception as exc: st.caption(f"Experiment registry unavailable: {exc}")

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

st.divider(); st.subheader("7. Classification benchmarking and calibration")
st.caption("Classification uses stratified animal-grouped folds. Probability calibration is assessed from out-of-fold class predictions when probabilities are available; this release reports calibration diagnostics but does not yet provide nested, group-aware recalibration of each classifier.")
class_target=st.selectbox("Categorical target",[c for c in df.columns if c not in features+[animal] and df[c].nunique(dropna=True)>=2],key="r62_class_target") if any(c for c in df.columns if c not in features+[animal] and df[c].nunique(dropna=True)>=2) else None
if class_target:
    class_models=st.multiselect("Classifiers",list(CLASSIFIERS),default=list(CLASSIFIERS),key="r62_class_models")
    if st.button("Run animal-grouped classification benchmark",key="r62_class_run",disabled=not class_models):
        try:
            scores,matrices,labels=grouped_classification_benchmark(df,class_target,features,animal,selected_models=class_models,n_splits=5,seed=int(seed))
            st.session_state["r62_classification"]=(scores,matrices,labels)
        except Exception as e: st.error(str(e))
    if "r62_classification" in st.session_state:
        scores,matrices,labels=st.session_state["r62_classification"]; st.dataframe(scores,use_container_width=True,hide_index=True)
        st.download_button("Download classification metrics",scores.to_csv(index=False).encode(),"grouped_classification_benchmark.csv")
        for name,matrix in matrices.items():
            st.markdown(f"**{name} — confusion matrix**"); st.dataframe(matrix,use_container_width=True)
else: st.info("No eligible categorical target with at least two observed classes was found outside the selected predictors and grouping variable.")

st.warning("Interpretation limits: SHAP and feature importance describe model reliance, not causal effects. Conformal coverage depends on exchangeability at the independent-group level. External validation requires a genuinely independent cohort and harmonised measurement protocol. Classification probability calibration remains a partial capability pending nested group-aware recalibration and full OOF probability diagnostics.")

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
