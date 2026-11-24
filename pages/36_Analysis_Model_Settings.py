"""Central configuration for reproducible statistical and ML analyses."""
import json
import streamlit as st
from analysis_engine.ui import header, render_sidebar_navigation

render_sidebar_navigation()
header("Analysis & model settings", "Configure scoped model hyperparameters, nested tuning, conventional model assumptions and experiment tracking.", badge="RELEASE 6.8")

DEFAULTS = {
    "schema_version": 2,
    "comparison": {"n_splits": 5, "n_boot": 500, "random_state": 42, "tune_models": False, "tuning_iter": 12, "tuning_method": "random"},
    "conventional": {"gee_covariance": "exchangeable", "mixed_reml": False, "quantile": 0.5, "spline_n_knots": 4},
    "preprocessing": {"numeric_imputation": "median", "categorical_imputation": "most_frequent", "scale_numeric": True},
    "models": {
        "Random Forest": {"n_estimators": 250, "max_depth": None, "min_samples_split": 2, "min_samples_leaf": 2, "max_features": 1.0, "bootstrap": True, "n_jobs": -1},
        "Extra Trees": {"n_estimators": 250, "max_depth": None, "min_samples_split": 2, "min_samples_leaf": 2, "max_features": 1.0, "bootstrap": False, "n_jobs": -1},
        "HistGradientBoosting": {"learning_rate": 0.1, "max_iter": 100, "max_leaf_nodes": 31, "max_depth": None, "min_samples_leaf": 20, "l2_regularization": 0.0},
        "SVR": {"kernel": "rbf", "C": 1.0, "epsilon": 0.1, "gamma": "scale"},
        "KNN": {"n_neighbors": 5, "weights": "distance", "p": 2, "leaf_size": 30}
    }
}

from analysis_engine.experiment_registry import load_settings, save_settings

# Scope settings by authenticated account (when available), project and species.
_identity = st.session_state.get("user_id") or st.session_state.get("username") or st.session_state.get("email")
_user_scope = str(_identity or "local-user")
if not _identity:
    st.warning("No authenticated user identifier was found in the Streamlit session. Settings will use the shared local-user scope; configure an authenticated user ID before enabling multi-user persistence.")
scope_a, scope_b = st.columns(2)
with scope_a: project_scope = st.text_input("Project / study scope", value=st.session_state.get("analysis_project_scope", "default-project"), key="analysis_project_input")
with scope_b: species_scope = st.selectbox("Species scope", ["all", "cattle", "sheep", "goats", "other"], index=0, key="analysis_species_input")
project_scope = project_scope.strip() or "default-project"
st.session_state["analysis_project_scope"] = project_scope
scope_key = f"{_user_scope}|{project_scope}|{species_scope}"
if st.session_state.get("analysis_settings_scope_key") != scope_key:
    persisted, persisted_at = load_settings(_user_scope, project_scope, species_scope)
    st.session_state.analysis_settings = persisted or json.loads(json.dumps(DEFAULTS))
    # Migrate configurations exported by Release 6.7.
    cfg = st.session_state.analysis_settings
    cfg.setdefault("schema_version", 2); cfg.setdefault("conventional", DEFAULTS["conventional"])
    cfg.setdefault("comparison", {}).setdefault("tune_models", False)
    cfg.setdefault("comparison", {}).setdefault("tuning_iter", 12)
    cfg.setdefault("comparison", {}).setdefault("tuning_method", "random")
    st.session_state.analysis_settings_scope_key = scope_key
    st.session_state.analysis_settings_saved_at = persisted_at
config = st.session_state.analysis_settings

st.info("Settings are persisted in a local SQLite registry and scoped by user, project and species. In a multi-user deployment, configure a shared durable registry path or integrate this registry with the platform's authenticated tenant database before treating it as centrally shared.")
if st.session_state.get("analysis_settings_saved_at"):
    st.caption(f"Last persisted: {st.session_state.analysis_settings_saved_at}")

with st.form("analysis_settings_form"):
    st.subheader("1. Validation and reproducibility")
    c1, c2, c3 = st.columns(3)
    with c1: n_splits = st.number_input("Grouped CV folds", 3, 10, int(config["comparison"]["n_splits"]))
    with c2: n_boot = st.selectbox("Cluster-bootstrap replicates", [200, 500, 1000, 2000, 5000], index=[200,500,1000,2000,5000].index(int(config["comparison"]["n_boot"])) if int(config["comparison"]["n_boot"]) in [200,500,1000,2000,5000] else 1)
    with c3: seed = st.number_input("Random seed", 0, 999999, int(config["comparison"]["random_state"]))
    tune_models = st.checkbox("Nested grouped hyperparameter optimisation for selected ML models", value=bool(config["comparison"].get("tune_models", False)))
    tuning_method = st.selectbox("Optimisation strategy", ["random", "grid", "bayesian"], index=["random", "grid", "bayesian"].index(config["comparison"].get("tuning_method", "random")))
    tuning_iter = st.slider("Random / Bayesian candidates per outer fold", 2, 40, int(config["comparison"].get("tuning_iter", 12)))
    st.caption("Grid search evaluates the defined grid; random search samples candidates; Bayesian search uses Optuna TPE and requires the optional optuna package.")
    st.caption("The number of folds must not exceed the number of independent groups. Bootstrap resampling uses the grouping unit selected in the analysis.")

    st.subheader("2. Preprocessing")
    p1, p2, p3 = st.columns(3)
    with p1: num_imp = st.selectbox("Numeric missing-value imputation", ["median", "mean"], index=["median","mean"].index(config["preprocessing"]["numeric_imputation"]))
    with p2: cat_imp = st.selectbox("Categorical imputation", ["most_frequent", "constant"], index=["most_frequent","constant"].index(config["preprocessing"]["categorical_imputation"]))
    with p3: scale = st.checkbox("Standardise numeric predictors", value=bool(config["preprocessing"]["scale_numeric"]))
    st.caption("Imputation and scaling are fitted inside each training fold to reduce leakage. Categorical predictors are one-hot encoded.")

    st.subheader("3. Conventional statistical model assumptions")
    conv = config.get("conventional", DEFAULTS["conventional"])
    a,b,c,d = st.columns(4)
    with a: gee_cov = st.selectbox("GEE working correlation", ["exchangeable", "independence"], index=["exchangeable","independence"].index(conv["gee_covariance"]))
    with b: mixed_reml = st.checkbox("Mixed-effects REML estimation", value=bool(conv["mixed_reml"]))
    with c: quantile = st.selectbox("Quantile regression τ", [0.1,0.25,0.5,0.75,0.9], index=[0.1,0.25,0.5,0.75,0.9].index(float(conv["quantile"])))
    with d: spline_knots = st.slider("Spline basis knots", 3, 8, int(conv["spline_n_knots"]))
    st.caption("GEE covariance is a working correlation assumption. REML is used for variance-component estimation; predictive comparisons remain based on held-out predictions.")

    st.subheader("4. Random Forest")
    rf = config["models"]["Random Forest"]
    a,b,c = st.columns(3)
    with a: rf_n = st.number_input("Trees", 50, 2000, int(rf["n_estimators"]), 50, key="rf_n")
    with b: rf_depth = st.selectbox("Maximum depth", ["None", 5, 10, 20, 30, 50], index=0 if rf["max_depth"] is None else ["None",5,10,20,30,50].index(rf["max_depth"]), key="rf_depth")
    with c: rf_leaf = st.number_input("Minimum leaf samples", 1, 50, int(rf["min_samples_leaf"]), key="rf_leaf")
    rf_split = st.number_input("Minimum split samples", 2, 50, int(rf["min_samples_split"]), key="rf_split")

    st.subheader("5. Extra Trees")
    et = config["models"]["Extra Trees"]
    a,b,c = st.columns(3)
    with a: et_n = st.number_input("Trees", 50, 2000, int(et["n_estimators"]), 50, key="et_n")
    with b: et_depth = st.selectbox("Maximum depth", ["None", 5, 10, 20, 30, 50], index=0 if et["max_depth"] is None else ["None",5,10,20,30,50].index(et["max_depth"]), key="et_depth")
    with c: et_leaf = st.number_input("Minimum leaf samples", 1, 50, int(et["min_samples_leaf"]), key="et_leaf")
    et_split = st.number_input("Minimum split samples", 2, 50, int(et["min_samples_split"]), key="et_split")

    st.subheader("6. Histogram Gradient Boosting")
    hg = config["models"]["HistGradientBoosting"]
    a,b,c = st.columns(3)
    with a: hg_rate = st.number_input("Learning rate", 0.001, 1.0, float(hg["learning_rate"]), 0.01, format="%.3f")
    with b: hg_iter = st.number_input("Boosting iterations", 50, 2000, int(hg["max_iter"]), 50)
    with c: hg_leaf = st.number_input("Maximum leaf nodes", 5, 255, int(hg["max_leaf_nodes"]))
    hg_depth = st.selectbox("Maximum tree depth", ["None", 2, 3, 5, 8, 12], index=0 if hg["max_depth"] is None else ["None",2,3,5,8,12].index(hg["max_depth"]))
    hg_minleaf = st.number_input("Minimum samples per leaf", 5, 100, int(hg["min_samples_leaf"]))
    hg_l2 = st.number_input("L2 regularisation", 0.0, 100.0, float(hg["l2_regularization"]), 0.1)

    st.subheader("7. Support Vector Regression")
    svr = config["models"]["SVR"]
    a,b,c = st.columns(3)
    with a: svr_kernel = st.selectbox("Kernel", ["rbf", "linear", "poly", "sigmoid"], index=["rbf","linear","poly","sigmoid"].index(svr["kernel"]))
    with b: svr_c = st.number_input("C (regularisation)", 0.001, 10000.0, float(svr["C"]), format="%.3f")
    with c: svr_eps = st.number_input("Epsilon", 0.001, 10.0, float(svr["epsilon"]), format="%.3f")
    svr_gamma = st.selectbox("Gamma", ["scale", "auto"], index=["scale","auto"].index(svr["gamma"]))

    st.subheader("8. K-Nearest Neighbours")
    knn = config["models"]["KNN"]
    a,b,c = st.columns(3)
    with a: knn_k = st.number_input("Number of neighbours", 1, 100, int(knn["n_neighbors"]))
    with b: knn_weights = st.selectbox("Neighbour weights", ["uniform", "distance"], index=["uniform","distance"].index(knn["weights"]))
    with c: knn_p = st.selectbox("Minkowski distance power", [1,2], index=[1,2].index(int(knn["p"])))
    knn_leaf = st.number_input("Leaf size", 5, 100, int(knn["leaf_size"]))

    submitted = st.form_submit_button("Save analysis settings", type="primary", use_container_width=True)

if submitted:
    config["comparison"] = {"n_splits": int(n_splits), "n_boot": int(n_boot), "random_state": int(seed), "tune_models": bool(tune_models), "tuning_iter": int(tuning_iter), "tuning_method": tuning_method}
    config["conventional"] = {"gee_covariance": gee_cov, "mixed_reml": bool(mixed_reml), "quantile": float(quantile), "spline_n_knots": int(spline_knots)}
    config["preprocessing"] = {"numeric_imputation": num_imp, "categorical_imputation": cat_imp, "scale_numeric": bool(scale)}
    config["models"] = {
        "Random Forest": {"n_estimators": int(rf_n), "max_depth": None if rf_depth == "None" else int(rf_depth), "min_samples_split": int(rf_split), "min_samples_leaf": int(rf_leaf), "max_features": rf["max_features"], "bootstrap": True, "n_jobs": -1},
        "Extra Trees": {"n_estimators": int(et_n), "max_depth": None if et_depth == "None" else int(et_depth), "min_samples_split": int(et_split), "min_samples_leaf": int(et_leaf), "max_features": et["max_features"], "bootstrap": False, "n_jobs": -1},
        "HistGradientBoosting": {"learning_rate": float(hg_rate), "max_iter": int(hg_iter), "max_leaf_nodes": int(hg_leaf), "max_depth": None if hg_depth == "None" else int(hg_depth), "min_samples_leaf": int(hg_minleaf), "l2_regularization": float(hg_l2)},
        "SVR": {"kernel": svr_kernel, "C": float(svr_c), "epsilon": float(svr_eps), "gamma": svr_gamma},
        "KNN": {"n_neighbors": int(knn_k), "weights": knn_weights, "p": int(knn_p), "leaf_size": int(knn_leaf)}
    }
    st.session_state.analysis_settings = config
    stamp = save_settings(_user_scope, project_scope, species_scope, config)
    st.session_state.analysis_settings_saved_at = stamp
    st.success("Settings saved persistently for this user, project and species scope.")

st.divider()
st.subheader("9. Configuration management")
st.download_button("Export settings (JSON)", json.dumps(config, indent=2).encode("utf-8"), "methane_analysis_settings.json", "application/json")
config_upload = st.file_uploader("Import a previously exported settings JSON", type=["json"], key="settings_import")
if config_upload is not None and st.button("Validate and import settings"):
    try:
        incoming = json.load(config_upload)
        if incoming.get("schema_version") not in (1, 2) or set(incoming.get("models", {})) != set(DEFAULTS["models"]):
            raise ValueError("Unsupported settings schema or incomplete model catalogue.")
        incoming.setdefault("conventional", DEFAULTS["conventional"])
        incoming.setdefault("comparison", {}).setdefault("tune_models", False)
        incoming.setdefault("comparison", {}).setdefault("tuning_iter", 12)
        incoming.setdefault("comparison", {}).setdefault("tuning_method", "random")
        incoming["schema_version"] = 2
        # Validate estimator parameter names and values against installed sklearn estimators.
        from analysis_engine.model_comparison import ML_MODELS
        for name, params in incoming["models"].items():
            allowed = ML_MODELS[name].get_params(deep=False)
            unknown = set(params) - set(allowed)
            if unknown: raise ValueError(f"Unknown parameters for {name}: {sorted(unknown)}")
        st.session_state.analysis_settings = incoming
        stamp = save_settings(_user_scope, project_scope, species_scope, incoming)
        st.session_state.analysis_settings_saved_at = stamp
        st.success("Configuration imported and persisted for the selected scope.")
        st.rerun()
    except Exception as exc:
        st.error(f"Settings import rejected: {exc}")

if st.button("Restore default settings"):
    st.session_state.analysis_settings = json.loads(json.dumps(DEFAULTS))
    stamp = save_settings(_user_scope, project_scope, species_scope, st.session_state.analysis_settings)
    st.session_state.analysis_settings_saved_at = stamp
    st.success("Defaults restored and persisted for the selected scope.")
    st.rerun()
