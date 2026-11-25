"""Central, versioned configuration for the complete methane analytics workflow."""
import copy, json
import streamlit as st
from analysis_engine.ui import header, render_sidebar_navigation
from analysis_engine.experiment_registry import load_settings, save_settings, save_settings_snapshot, list_settings_snapshots
from analysis_engine.settings_config import defaults, migrate_settings, validate_settings, config_fingerprint

render_sidebar_navigation()
header("Analysis & model settings", "Central configuration for study design, preprocessing, inference, machine learning, clustering, repeatability, forecasting and reproducible reporting.", badge="RELEASE 6.10")

identity = st.session_state.get("user_id") or st.session_state.get("username") or st.session_state.get("email")
user_scope = str(identity or "local-user")
if not identity:
    st.warning("No authenticated user identifier was found. Settings use the shared local-user scope; configure authenticated identity before enabling multi-user use.")
ca, cb = st.columns(2)
with ca: project_scope = st.text_input("Project / study scope", value=st.session_state.get("analysis_project_scope", "default-project"), key="analysis_project_input")
with cb: species_scope = st.selectbox("Species scope", ["all", "cattle", "sheep", "goats", "buffalo", "camel", "other"], key="analysis_species_input")
project_scope = project_scope.strip() or "default-project"
st.session_state["analysis_project_scope"] = project_scope
st.session_state["analysis_species_scope"] = species_scope
scope_key = f"{user_scope}|{project_scope}|{species_scope}"
if st.session_state.get("analysis_settings_scope_key") != scope_key:
    persisted, persisted_at = load_settings(user_scope, project_scope, species_scope)
    st.session_state.analysis_settings = migrate_settings(persisted or {})
    st.session_state.analysis_settings_scope_key = scope_key
    st.session_state.analysis_settings_saved_at = persisted_at
cfg = migrate_settings(st.session_state.get("analysis_settings", {}))
if st.session_state.get("analysis_settings_saved_at"):
    st.caption(f"Last saved: {st.session_state.analysis_settings_saved_at}")
st.info("Configuration precedence: global defaults → project/species settings → analysis-level overrides. This page persists project/species settings in SQLite. Analysis modules must explicitly consume a setting to apply it; saved configuration alone does not change an analysis implementation.")

with st.form("complete_analysis_settings"):
    tabs = st.tabs(["Study & data", "Preprocessing", "Statistics", "Machine learning", "Clustering", "Repeatability", "Forecasting", "Evaluation", "Reporting"])
    s=cfg["study"]
    with tabs[0]:
        st.subheader("Study design and variable mapping")
        a,b,c=st.columns(3)
        with a: study_name=st.text_input("Study name",s["name"]); species=st.selectbox("Species",["cattle","sheep","goats","buffalo","camel","other"],index=["cattle","sheep","goats","buffalo","camel","other"].index(s["species"]))
        with b: design=st.selectbox("Study design",["cross-sectional","longitudinal","repeated measures","mixed"],index=["cross-sectional","longitudinal","repeated measures","mixed"].index(s["design"])); unit=st.selectbox("Experimental unit",["animal","herd","farm","site"],index=["animal","herd","farm","site"].index(s["experimental_unit"]))
        with c: animal_id=st.text_input("Animal identifier column",s["animal_id"]); group_id=st.text_input("Higher-level group column",s["group_id"])
        a,b=st.columns(2)
        with a: date_col=st.text_input("Measurement date column",s["date_column"]); round_col=st.text_input("Measurement round/session column",s["round_column"])
        with b: methane_targets=st.text_input("Methane target columns (comma-separated)",", ".join(s["methane_targets"])); predictors=st.text_input("Phenotypic predictor columns (comma-separated)",", ".join(s["phenotype_predictors"]))
        a,b,c=st.columns(3)
        with a: units=st.text_input("Measurement units",s["measurement_unit"])
        with b: protocol=st.text_input("Measurement protocol",s["protocol"])
        with c: instrument=st.text_input("Instrument / method",s["instrument"])
        calibration=st.text_input("Calibration details",s["calibration"]); min_duration=st.number_input("Minimum valid measurement duration (minutes; 0 = not enforced)",0,10000,int(s["minimum_duration"]))
    p=cfg["preprocessing"]
    with tabs[1]:
        st.subheader("Data quality and preprocessing")
        a,b,c=st.columns(3)
        with a: num_imp=st.selectbox("Numeric imputation",["median","mean","knn","iterative","complete_case"],index=["median","mean","knn","iterative","complete_case"].index(p["numeric_imputation"]))
        with b: cat_imp=st.selectbox("Categorical imputation",["most_frequent","constant","complete_case"],index=["most_frequent","constant","complete_case"].index(p["categorical_imputation"]))
        with c: miss=st.slider("Missingness threshold (%)",0,100,int(p["missing_threshold_pct"]))
        a,b,c=st.columns(3)
        with a: out_method=st.selectbox("Outlier detection",["IQR","Z-score","robust Z-score","Isolation Forest","none"],index=["IQR","Z-score","robust Z-score","Isolation Forest","none"].index(p["outlier_method"]))
        with b: out_action=st.selectbox("Outlier action",["flag","retain","winsorise","exclude"],index=["flag","retain","winsorise","exclude"].index(p["outlier_action"]))
        with c: out_threshold=st.number_input("Outlier threshold",0.1,10.0,float(p["outlier_threshold"]),0.1)
        a,b=st.columns(2)
        with a: duplicate_action=st.selectbox("Duplicate records",["flag","remove exact duplicates","retain"],index=["flag","remove exact duplicates","retain"].index(p["duplicate_action"]))
        with b: transform=st.selectbox("Transformation",["none","log","square_root","Box-Cox","Yeo-Johnson"],index=["none","log","square_root","Box-Cox","Yeo-Johnson"].index(p["transformation"]))
        scaling=st.selectbox("Scaling",["none","standard","minmax","robust"],index=["none","standard","minmax","robust"].index(p["scaling"]))
        st.caption("Imputation/scaling must be fitted within training folds. Preserve raw observations and report every flagged, transformed or excluded record.")
    q=cfg["statistics"]
    with tabs[2]:
        st.subheader("Conventional statistical inference")
        a,b,c=st.columns(3)
        with a: alpha=st.selectbox("Significance level (α)",[0.01,0.05,0.10],index=[0.01,0.05,0.10].index(float(q["alpha"]))); conf=st.selectbox("Confidence interval",[0.90,0.95,0.99],index=[0.90,0.95,0.99].index(float(q["confidence_level"])))
        with b: multiple=st.selectbox("Multiple-testing correction",["holm","bonferroni","fdr_bh","tukey","none"],index=["holm","bonferroni","fdr_bh","tukey","none"].index(q["multiple_testing"])); normality=st.selectbox("Normality test",["shapiro","anderson","dagostino"],index=["shapiro","anderson","dagostino"].index(q["normality_test"]))
        with c: variance=st.selectbox("Variance homogeneity",["levene","bartlett","fligner"],index=["levene","bartlett","fligner"].index(q["variance_test"])); boot=st.number_input("Bootstrap iterations",100,20000,int(q["bootstrap_iterations"]),100)
        correlations=st.multiselect("Correlation methods",["pearson","spearman","kendall"],default=q["correlations"]); effects=st.multiselect("Effect sizes",["cohen_d","hedges_g","eta_squared","epsilon_squared","omega_squared","rank_biserial"],default=q["effect_sizes"])
        repeated=st.selectbox("Repeated-measures method",["mixed_effects","repeated_measures_anova","friedman","gee"],index=["mixed_effects","repeated_measures_anova","friedman","gee"].index(q["repeated_method"]))
        a,b,c=st.columns(3)
        with a: random_intercept=st.checkbox("Animal random intercept",bool(q["random_intercept"]))
        with b: random_slope=st.checkbox("Time/round random slope",bool(q["random_slope"]))
        with c: sph=st.selectbox("Sphericity correction",["GG","HF","none"],index=["GG","HF","none"].index(q["sphericity_correction"]))
        conv=cfg["conventional"]
        gee=st.selectbox("GEE working correlation",["exchangeable","independence","autoregressive","unstructured"],index=["exchangeable","independence","autoregressive","unstructured"].index(conv["gee_covariance"]))
        reml=st.checkbox("Use REML for mixed-model variance components",bool(conv["mixed_reml"]))
        tau=st.selectbox("Quantile regression τ",[0.1,0.25,0.5,0.75,0.9],index=[0.1,0.25,0.5,0.75,0.9].index(float(conv["quantile"])))
        knots=st.slider("Spline basis knots",3,10,int(conv["spline_n_knots"]))
    m=cfg["comparison"]
    with tabs[3]:
        st.subheader("Machine learning validation and optimisation")
        a,b,c=st.columns(3)
        with a: folds=st.number_input("Cross-validation folds",2,10,int(m["n_splits"])); test_size=st.slider("Test set proportion",0.1,0.4,float(m["test_size"]),0.05)
        with b: validation=st.selectbox("Validation strategy",["grouped","temporal","random","leave_one_group_out"],index=["grouped","temporal","random","leave_one_group_out"].index(m["validation_strategy"])); group_column=st.text_input("Grouping variable",m["group_column"])
        with c: seed=st.number_input("Random seed",0,999999,int(m["random_state"])); nboot=st.selectbox("Cluster bootstrap replicates",[200,500,1000,2000,5000],index=[200,500,1000,2000,5000].index(int(m["n_boot"])))
        tune=st.checkbox("Nested hyperparameter optimisation",bool(m["tune_models"])); method=st.selectbox("Optimisation method",["random","grid","bayesian"],index=["random","grid","bayesian"].index(m["tuning_method"])); iterations=st.slider("Candidates per outer fold",2,200,int(m["tuning_iter"]))
        a,b=st.columns(2)
        with a: feature_selection=st.selectbox("Feature selection",["none","correlation","RFE","Boruta","permutation"],index=["none","correlation","RFE","Boruta","permutation"].index(m["feature_selection"]))
        with b: imbalance=st.selectbox("Class imbalance",["class_weight","SMOTE","undersampling","none"],index=["class_weight","SMOTE","undersampling","none"].index(m["class_imbalance"]))
        interpretation=st.multiselect("Model interpretation",["permutation","SHAP"],default=m["interpretation"])
        st.caption("Grouped validation is preferred for repeated animal records. Temporal validation is required for forward-looking prediction. Bayesian optimisation requires Optuna; SMOTE requires imbalanced-learn.")
        st.markdown("**Model hyperparameters**")
        model_cfg=copy.deepcopy(cfg["models"])
        with st.expander("Random Forest / Extra Trees"):
            a,b,c=st.columns(3)
            with a: rf_trees=st.number_input("RF trees",50,2000,int(model_cfg["Random Forest"]["n_estimators"]),50); et_trees=st.number_input("Extra Trees",50,2000,int(model_cfg["Extra Trees"]["n_estimators"]),50)
            with b: rf_depth=st.selectbox("RF max depth",["None",5,10,20,30,50],index=0 if model_cfg["Random Forest"]["max_depth"] is None else ["None",5,10,20,30,50].index(model_cfg["Random Forest"]["max_depth"])); et_depth=st.selectbox("Extra Trees max depth",["None",5,10,20,30,50],index=0 if model_cfg["Extra Trees"]["max_depth"] is None else ["None",5,10,20,30,50].index(model_cfg["Extra Trees"]["max_depth"]))
            with c: rf_leaf=st.number_input("RF min leaf",1,50,int(model_cfg["Random Forest"]["min_samples_leaf"])); et_leaf=st.number_input("ET min leaf",1,50,int(model_cfg["Extra Trees"]["min_samples_leaf"]))
        with st.expander("Gradient boosting / SVR / KNN"):
            hg=model_cfg["HistGradientBoosting"]; sv=model_cfg["SVR"]; kn=model_cfg["KNN"]
            a,b,c=st.columns(3)
            with a: hg_rate=st.number_input("HGB learning rate",0.001,1.0,float(hg["learning_rate"]),0.01); svr_kernel=st.selectbox("SVR kernel",["rbf","linear","poly","sigmoid"],index=["rbf","linear","poly","sigmoid"].index(sv["kernel"]))
            with b: hg_iter=st.number_input("HGB iterations",50,2000,int(hg["max_iter"]),50); svr_c=st.number_input("SVR C",0.001,10000.0,float(sv["C"]))
            with c: hg_leaf=st.number_input("HGB leaf nodes",5,255,int(hg["max_leaf_nodes"])); svr_eps=st.number_input("SVR epsilon",0.001,10.0,float(sv["epsilon"]))
            a,b=st.columns(2)
            with a: knn_k=st.number_input("KNN neighbours",1,100,int(kn["n_neighbors"]))
            with b: knn_weights=st.selectbox("KNN weights",["uniform","distance"],index=["uniform","distance"].index(kn["weights"])); svr_gamma=st.selectbox("SVR gamma",["scale","auto"],index=["scale","auto"].index(sv["gamma"]))
    cl=cfg["clustering"]
    with tabs[4]:
        st.subheader("Clustering and dimensionality reduction")
        algorithms=st.multiselect("Clustering algorithms",["kmeans","hierarchical","dbscan","gaussian_mixture"],default=cl["algorithms"])
        a,b,c=st.columns(3)
        with a: min_k=st.number_input("Minimum clusters",2,20,int(cl["min_clusters"])); max_k=st.number_input("Maximum clusters",2,30,int(cl["max_clusters"]))
        with b: distance=st.selectbox("Distance metric",["euclidean","manhattan","cosine"],index=["euclidean","manhattan","cosine"].index(cl["distance"])); linkage=st.selectbox("Hierarchical linkage",["ward","complete","average","single"],index=["ward","complete","average","single"].index(cl["linkage"]))
        with c: pca_var=st.selectbox("PCA cumulative variance target",[0.80,0.90,0.95,0.99],index=[0.80,0.90,0.95,0.99].index(float(cl["pca_variance"]))); umap_n=st.number_input("UMAP neighbours",2,100,int(cl["umap_neighbors"]))
        umap_dist=st.slider("UMAP minimum distance",0.0,0.99,float(cl["umap_min_dist"]),0.01)
        st.caption("Cluster number selection should consider silhouette, Davies–Bouldin and Calinski–Harabasz together, alongside biological interpretability.")
    r=cfg["repeatability"]
    with tabs[5]:
        st.subheader("Repeatability and longitudinal structure")
        a,b,c=st.columns(3)
        with a: rep_animal=st.text_input("Animal identifier",r["animal_column"]); rep_occasion=st.text_input("Measurement occasion",r["occasion_column"])
        with b: icc=st.selectbox("ICC formulation",["ICC(1,1)","ICC(2,1)","ICC(3,1)","ICC(1,k)","ICC(2,k)","ICC(3,k)"],index=["ICC(1,1)","ICC(2,1)","ICC(3,1)","ICC(1,k)","ICC(2,k)","ICC(3,k)"].index(r["icc_type"])); rep_conf=st.selectbox("ICC confidence level",[0.90,0.95,0.99],index=[0.90,0.95,0.99].index(float(r["confidence_level"])))
        with c: min_reps=st.number_input("Minimum observations per animal",2,20,int(r["minimum_measurements"])); rep_slope=st.checkbox("Include random time slope",bool(r["include_random_slope"]))
        within=st.multiselect("Within-animal variability metrics",["sd","cv","mad","iqr"],default=r["within_animal_metrics"])
        st.warning("ICC/repeatability is not heritability. Genetic heritability requires pedigree/genomic relationships and an appropriate genetic model.")
    f=cfg["forecasting"]
    with tabs[6]:
        st.subheader("Time-series forecasting")
        a,b,c=st.columns(3)
        with a: freq=st.selectbox("Frequency",["D","W","ME"],index=["D","W","ME"].index(f["frequency"])); aggregation=st.selectbox("Within-period aggregation",["mean","median"],index=["mean","median"].index(f["aggregation"]))
        with b: horizon=st.number_input("Forecast horizon",1,365,int(f["horizon"])); test_fraction=st.slider("Chronological holdout",0.1,0.4,float(f["test_fraction"]),0.05)
        with c: season=st.number_input("Seasonal period",2,365,int(f["seasonal_period"])); rolling=st.checkbox("Enable rolling-origin backtesting",bool(f["rolling_origin"]))
        forecast_models=st.multiselect("Forecast models",["Naive","Seasonal Naive","ARIMA","SARIMA","Prophet","SVR","LSTM"],default=f["models"])
        a,b,c=st.columns(3)
        with a: ap=st.number_input("ARIMA p",0,8,int(f["arima_order"][0])); ad=st.number_input("ARIMA d",0,2,int(f["arima_order"][1])); aq=st.number_input("ARIMA q",0,8,int(f["arima_order"][2]))
        with b: sp=st.number_input("SARIMA P",0,5,int(f["sarima_order"][0])); sd=st.number_input("SARIMA D",0,2,int(f["sarima_order"][1])); sq=st.number_input("SARIMA Q",0,5,int(f["sarima_order"][2]))
        with c: svr_lags=st.number_input("SVR lag features",2,100,int(f["svr_lags"])); svr_fc_kernel=st.selectbox("Forecast SVR kernel",["rbf","linear","poly"],index=["rbf","linear","poly"].index(f["svr_kernel"]))
        a,b,c=st.columns(3)
        with a: prophet_yearly=st.checkbox("Prophet yearly seasonality",bool(f["prophet_yearly"])); prophet_weekly=st.checkbox("Prophet weekly seasonality",bool(f["prophet_weekly"]))
        with b: lstm_look=st.number_input("LSTM lookback",2,100,int(f["lstm_lookback"])); lstm_units=st.number_input("LSTM units",4,256,int(f["lstm_units"]))
        with c: lstm_epochs=st.number_input("LSTM epochs",10,1000,int(f["lstm_epochs"])); lstm_batch=st.number_input("LSTM batch size",4,256,int(f["lstm_batch_size"]))
        a,b=st.columns(2)
        with a: lstm_lr=st.number_input("LSTM learning rate",0.00001,0.1,float(f["lstm_learning_rate"]),format="%.5f")
        with b: pi=st.selectbox("Forecast interval level",[0.80,0.90,0.95,0.99],index=[0.80,0.90,0.95,0.99].index(float(f["prediction_interval"])))
        st.caption("Season length must reflect sampling cadence and a defensible biological/operational cycle. Forecasting requires temporal replication; irregular gaps must be handled without collapsing time indices.")
    e=cfg["evaluation"]
    with tabs[7]:
        st.subheader("Performance metrics and diagnostics")
        reg_metrics=st.multiselect("Regression metrics",["R2","adjusted_R2","MAE","RMSE","MSE","MAPE","MedAE"],default=e["regression_metrics"])
        cls_metrics=st.multiselect("Classification metrics",["accuracy","balanced_accuracy","precision","recall","F1","ROC_AUC","PR_AUC","MCC"],default=e["classification_metrics"])
        a,b,c=st.columns(3)
        with a: residual_diag=st.checkbox("Residual diagnostics",bool(e["residual_diagnostics"]))
        with b: acf_diag=st.checkbox("Autocorrelation diagnostics",bool(e["autocorrelation_diagnostics"]))
        with c: criterion=st.selectbox("Model selection criterion",["cross_validation","AIC","BIC","RMSE","MAE","ROC_AUC"],index=["cross_validation","AIC","BIC","RMSE","MAE","ROC_AUC"].index(e["selection_criterion"]))
        intervals=st.multiselect("Prediction interval levels",[0.8,0.9,0.95,0.99],default=e["prediction_intervals"])
        st.caption("MAPE is not appropriate for zero or near-zero outcomes. Use scale-aware metrics such as MAE/RMSE when this occurs.")
    o=cfg["reporting"]
    with tabs[8]:
        st.subheader("Reporting and reproducibility")
        formats=st.multiselect("Report formats",["PDF","DOCX","XLSX"],default=o["formats"]); fig_formats=st.multiselect("Figure formats",["PNG","SVG","TIFF"],default=o["figure_formats"])
        a,b,c=st.columns(3)
        with a: dpi=st.selectbox("Figure resolution (DPI)",[150,300,600],index=[150,300,600].index(int(o["dpi"]))); decimals=st.number_input("Decimal places",1,6,int(o["decimals"]))
        with b: inc_method=st.checkbox("Include methodology",bool(o["include_methodology"])); inc_params=st.checkbox("Include model parameters",bool(o["include_parameters"]))
        with c: inc_diag=st.checkbox("Include diagnostics",bool(o["include_diagnostics"])); inc_dict=st.checkbox("Include data dictionary",bool(o["include_dictionary"]))
        save_versions=st.checkbox("Retain immutable configuration snapshots",bool(o["save_versions"]))
    submitted=st.form_submit_button("Save all settings",type="primary",use_container_width=True)

if submitted:
    cfg["study"]={"name":study_name,"species":species,"design":design,"experimental_unit":unit,"animal_id":animal_id,"group_id":group_id,"date_column":date_col,"round_column":round_col,"methane_targets":[x.strip() for x in methane_targets.split(",") if x.strip()],"phenotype_predictors":[x.strip() for x in predictors.split(",") if x.strip()],"measurement_unit":units,"protocol":protocol,"instrument":instrument,"calibration":calibration,"minimum_duration":int(min_duration)}
    cfg["preprocessing"]={"numeric_imputation":num_imp,"categorical_imputation":cat_imp,"missing_threshold_pct":int(miss),"outlier_method":out_method,"outlier_action":out_action,"outlier_threshold":float(out_threshold),"duplicate_action":duplicate_action,"transformation":transform,"scaling":scaling,"scale_numeric":scaling!="none"}
    cfg["statistics"]={"alpha":float(alpha),"confidence_level":float(conf),"multiple_testing":multiple,"normality_test":normality,"variance_test":variance,"correlations":correlations,"effect_sizes":effects,"bootstrap_iterations":int(boot),"repeated_method":repeated,"random_intercept":bool(random_intercept),"random_slope":bool(random_slope),"sphericity_correction":sph}
    cfg["comparison"]={"n_splits":int(folds),"n_boot":int(nboot),"random_state":int(seed),"test_size":float(test_size),"validation_strategy":validation,"group_column":group_column,"tune_models":bool(tune),"tuning_iter":int(iterations),"tuning_method":method,"feature_selection":feature_selection,"class_imbalance":imbalance,"interpretation":interpretation}
    cfg["conventional"]={"gee_covariance":gee,"mixed_reml":bool(reml),"quantile":float(tau),"spline_n_knots":int(knots)}
    cfg["models"]["Random Forest"].update({"n_estimators":int(rf_trees),"max_depth":None if rf_depth=="None" else int(rf_depth),"min_samples_leaf":int(rf_leaf)})
    cfg["models"]["Extra Trees"].update({"n_estimators":int(et_trees),"max_depth":None if et_depth=="None" else int(et_depth),"min_samples_leaf":int(et_leaf)})
    cfg["models"]["HistGradientBoosting"].update({"learning_rate":float(hg_rate),"max_iter":int(hg_iter),"max_leaf_nodes":int(hg_leaf)})
    cfg["models"]["SVR"].update({"kernel":svr_kernel,"C":float(svr_c),"epsilon":float(svr_eps),"gamma":svr_gamma})
    cfg["models"]["KNN"].update({"n_neighbors":int(knn_k),"weights":knn_weights})
    cfg["clustering"]={"algorithms":algorithms,"min_clusters":int(min_k),"max_clusters":int(max_k),"distance":distance,"linkage":linkage,"pca_variance":float(pca_var),"umap_neighbors":int(umap_n),"umap_min_dist":float(umap_dist)}
    cfg["repeatability"]={"animal_column":rep_animal,"occasion_column":rep_occasion,"icc_type":icc,"confidence_level":float(rep_conf),"minimum_measurements":int(min_reps),"include_random_slope":bool(rep_slope),"within_animal_metrics":within}
    cfg["forecasting"]={"frequency":freq,"aggregation":aggregation,"horizon":int(horizon),"test_fraction":float(test_fraction),"models":forecast_models,"arima_order":[int(ap),int(ad),int(aq)],"sarima_order":[int(sp),int(sd),int(sq),int(season)],"seasonal_period":int(season),"prophet_yearly":bool(prophet_yearly),"prophet_weekly":bool(prophet_weekly),"svr_kernel":svr_fc_kernel,"svr_c":float(svr_c),"svr_epsilon":float(svr_eps),"svr_gamma":svr_gamma,"svr_lags":int(svr_lags),"lstm_lookback":int(lstm_look),"lstm_units":int(lstm_units),"lstm_epochs":int(lstm_epochs),"lstm_batch_size":int(lstm_batch),"lstm_learning_rate":float(lstm_lr),"rolling_origin":bool(rolling),"prediction_interval":float(pi)}
    cfg["evaluation"]={"regression_metrics":reg_metrics,"classification_metrics":cls_metrics,"residual_diagnostics":bool(residual_diag),"autocorrelation_diagnostics":bool(acf_diag),"prediction_intervals":intervals,"selection_criterion":criterion}
    cfg["reporting"]={"formats":formats,"figure_formats":fig_formats,"dpi":int(dpi),"decimals":int(decimals),"include_methodology":bool(inc_method),"include_parameters":bool(inc_params),"include_diagnostics":bool(inc_diag),"include_dictionary":bool(inc_dict),"save_versions":bool(save_versions)}
    errors,warnings=validate_settings(cfg)
    if errors:
        for msg in errors: st.error(msg)
    else:
        stamp=save_settings(user_scope,project_scope,species_scope,cfg)
        snapshot=save_settings_snapshot(user_scope,project_scope,species_scope,cfg) if cfg["reporting"]["save_versions"] else None
        st.session_state.analysis_settings=cfg; st.session_state.analysis_settings_saved_at=stamp
        st.success("All settings saved for the selected user, project and species scope.")
        if snapshot: st.caption(f"Immutable configuration snapshot: {snapshot['snapshot_id']} | SHA-256: {snapshot['fingerprint']}")
        for msg in warnings: st.warning(msg)
        st.rerun()

st.divider()
st.subheader("Configuration management")
current=st.session_state.get("analysis_settings",cfg)
a,b=st.columns(2)
with a: st.download_button("Export settings (JSON)",json.dumps(current,indent=2).encode(),"methane_analysis_settings_v3.json","application/json",use_container_width=True)
with b:
    if st.button("Restore defaults",use_container_width=True):
        fresh=defaults(); save_settings(user_scope,project_scope,species_scope,fresh); st.session_state.analysis_settings=fresh; st.success("Defaults restored and saved."); st.rerun()
upload=st.file_uploader("Import settings JSON",type=["json"],key="settings_v3_import")
if upload and st.button("Validate and import JSON"):
    try:
        incoming=migrate_settings(json.load(upload)); errors,warnings=validate_settings(incoming)
        if errors: raise ValueError(" ".join(errors))
        stamp=save_settings(user_scope,project_scope,species_scope,incoming); snap=save_settings_snapshot(user_scope,project_scope,species_scope,incoming)
        st.session_state.analysis_settings=incoming; st.session_state.analysis_settings_saved_at=stamp
        st.success(f"Imported and saved. Snapshot {snap['snapshot_id']}.")
        for msg in warnings: st.warning(msg)
        st.rerun()
    except Exception as exc: st.error(f"Import rejected: {exc}")
with st.expander("Configuration history"):
    history=list_settings_snapshots(user_scope,project_scope,species_scope,20)
    if history: st.dataframe(history,use_container_width=True,hide_index=True)
    else: st.caption("No immutable snapshots have been recorded for this scope yet.")
st.caption(f"Current configuration fingerprint: {config_fingerprint(current)}")
