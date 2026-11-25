"""Versioned, validated defaults for project-scoped methane analyses."""
from __future__ import annotations
import copy, hashlib, json

DEFAULT_SETTINGS = {
    "schema_version": 3,
    "study": {"name": "", "species": "other", "design": "longitudinal", "experimental_unit": "animal", "animal_id": "", "group_id": "", "date_column": "", "round_column": "", "methane_targets": [], "phenotype_predictors": [], "measurement_unit": "", "protocol": "", "instrument": "", "calibration": "", "minimum_duration": 0},
    "preprocessing": {"numeric_imputation": "median", "categorical_imputation": "most_frequent", "missing_threshold_pct": 40, "outlier_method": "IQR", "outlier_action": "flag", "outlier_threshold": 1.5, "duplicate_action": "flag", "transformation": "none", "scaling": "standard", "scale_numeric": True},
    "statistics": {"alpha": 0.05, "confidence_level": 0.95, "multiple_testing": "holm", "normality_test": "shapiro", "variance_test": "levene", "correlations": ["pearson", "spearman"], "effect_sizes": ["cohen_d", "hedges_g", "eta_squared", "epsilon_squared"], "bootstrap_iterations": 1000, "repeated_method": "mixed_effects", "random_intercept": True, "random_slope": False, "sphericity_correction": "GG"},
    "comparison": {"n_splits": 5, "n_boot": 1000, "random_state": 42, "test_size": 0.2, "validation_strategy": "grouped", "group_column": "AnimalID", "tune_models": False, "tuning_iter": 50, "tuning_method": "random", "feature_selection": "none", "class_imbalance": "class_weight", "interpretation": ["permutation"]},
    "conventional": {"gee_covariance": "exchangeable", "mixed_reml": True, "quantile": 0.5, "spline_n_knots": 4},
    "models": {
        "Random Forest": {"n_estimators": 250, "max_depth": None, "min_samples_split": 2, "min_samples_leaf": 2, "max_features": 1.0, "bootstrap": True, "n_jobs": -1},
        "Extra Trees": {"n_estimators": 250, "max_depth": None, "min_samples_split": 2, "min_samples_leaf": 2, "max_features": 1.0, "bootstrap": False, "n_jobs": -1},
        "HistGradientBoosting": {"learning_rate": 0.1, "max_iter": 100, "max_leaf_nodes": 31, "max_depth": None, "min_samples_leaf": 20, "l2_regularization": 0.0},
        "SVR": {"kernel": "rbf", "C": 1.0, "epsilon": 0.1, "gamma": "scale"},
        "KNN": {"n_neighbors": 5, "weights": "distance", "p": 2, "leaf_size": 30}},
    "clustering": {"algorithms": ["kmeans", "hierarchical", "dbscan", "gaussian_mixture"], "min_clusters": 2, "max_clusters": 10, "distance": "euclidean", "linkage": "ward", "pca_variance": 0.95, "umap_neighbors": 15, "umap_min_dist": 0.1},
    "repeatability": {"animal_column": "AnimalID", "occasion_column": "", "icc_type": "ICC(2,1)", "confidence_level": 0.95, "minimum_measurements": 2, "include_random_slope": False, "within_animal_metrics": ["sd", "cv", "mad"]},
    "forecasting": {"frequency": "W", "aggregation": "mean", "horizon": 4, "test_fraction": 0.2, "models": ["Naive", "Seasonal Naive", "ARIMA", "SARIMA", "SVR"], "arima_order": [1,1,1], "sarima_order": [1,0,1,4], "seasonal_period": 4, "prophet_yearly": True, "prophet_weekly": True, "svr_kernel": "rbf", "svr_c": 1.0, "svr_epsilon": 0.1, "svr_gamma": "scale", "svr_lags": 6, "lstm_lookback": 6, "lstm_units": 32, "lstm_epochs": 80, "lstm_batch_size": 16, "lstm_learning_rate": 0.001, "rolling_origin": False, "prediction_interval": 0.95},
    "evaluation": {"regression_metrics": ["R2", "MAE", "RMSE"], "classification_metrics": ["balanced_accuracy", "precision", "recall", "F1", "ROC_AUC", "PR_AUC"], "residual_diagnostics": True, "autocorrelation_diagnostics": True, "prediction_intervals": [0.8, 0.9, 0.95], "selection_criterion": "cross_validation"},
    "reporting": {"formats": ["PDF", "DOCX", "XLSX"], "figure_formats": ["PNG", "SVG", "TIFF"], "dpi": 300, "decimals": 3, "include_methodology": True, "include_parameters": True, "include_diagnostics": True, "include_dictionary": True, "save_versions": True}
}

def defaults(): return copy.deepcopy(DEFAULT_SETTINGS)

def migrate_settings(incoming):
    """Preserve recognised legacy values while filling new schema sections."""
    cfg = defaults()
    if isinstance(incoming, dict):
        for section, values in incoming.items():
            if section in cfg and isinstance(cfg[section], dict) and isinstance(values, dict):
                for key, value in values.items():
                    if key in cfg[section]: cfg[section][key] = value
    cfg["schema_version"] = 3
    return cfg

def validate_settings(cfg):
    errors=[]; warnings=[]
    if not 0 < float(cfg['statistics']['alpha']) < 1: errors.append('Significance level alpha must be between 0 and 1.')
    if not 0 < float(cfg['statistics']['confidence_level']) < 1: errors.append('Confidence level must be between 0 and 1.')
    if int(cfg['comparison']['n_splits']) < 2: errors.append('Cross-validation requires at least two folds.')
    if not 0 < float(cfg['comparison']['test_size']) < 1: errors.append('Test size must be between 0 and 1.')
    if int(cfg['clustering']['min_clusters']) < 2 or int(cfg['clustering']['max_clusters']) < int(cfg['clustering']['min_clusters']): errors.append('Invalid cluster search range.')
    if int(cfg['forecasting']['seasonal_period']) < 2: errors.append('Seasonal period must be at least 2.')
    if int(cfg['forecasting']['horizon']) < 1: errors.append('Forecast horizon must be positive.')
    if int(cfg['forecasting']['lstm_lookback']) < 2: errors.append('LSTM lookback must be at least 2.')
    if int(cfg['forecasting']['svr_lags']) < 2: errors.append('SVR lag count must be at least 2.')
    if not 0 < float(cfg['forecasting']['test_fraction']) < 1: errors.append('Forecast holdout fraction must be between 0 and 1.')
    if int(cfg['comparison']['tuning_iter']) < 1: errors.append('Hyperparameter tuning iterations must be positive.')
    if int(cfg['reporting']['decimals']) < 0 or int(cfg['reporting']['decimals']) > 10: errors.append('Reporting decimal places must be between 0 and 10.')
    if int(cfg['repeatability']['minimum_measurements']) < 2: errors.append('Repeatability requires at least two measurements per animal.')
    if not 0 < float(cfg['forecasting']['prediction_interval']) < 1: errors.append('Forecast prediction interval must be between 0 and 1.')
    interval_levels = cfg['evaluation'].get('prediction_intervals', [])
    if any(not 0 < float(level) < 1 for level in interval_levels): errors.append('Prediction interval levels must be between 0 and 1.')
    if cfg['comparison']['validation_strategy'] == 'grouped' and not str(cfg['comparison'].get('group_column', '')).strip():
        warnings.append('Grouped validation is selected but no grouping column is configured.')
    if cfg['study'].get('design') == 'longitudinal' and not (cfg['study'].get('date_column') or cfg['study'].get('round_column')):
        warnings.append('Longitudinal design is selected but neither a date nor measurement-round column is configured.')
    if int(cfg['reporting']['dpi']) not in (150, 300, 600): warnings.append('Figure DPI is non-standard; use 300 or 600 for publication figures.')
    if cfg['comparison']['validation_strategy'] == 'random': warnings.append('Random validation can leak repeated animal records across train/test. Prefer grouped or temporal validation where appropriate.')
    if 'Seasonal Naive' in cfg['forecasting']['models']: warnings.append('Seasonal Naïve requires enough contiguous training observations to cover the selected seasonal period.')
    return errors, warnings

def config_fingerprint(cfg):
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()

def load_active_settings(session_state):
    """Load scoped settings on demand so analysis pages work even if Settings was not visited first."""
    from analysis_engine.experiment_registry import load_settings
    principal = session_state.get("principal") or {}
    identity = (session_state.get("user_id") or principal.get("subject") or
                session_state.get("username") or session_state.get("email"))
    user_scope = str(identity or "local-user")
    if identity:
        session_state["user_id"] = str(identity)
    project_scope = str(session_state.get("analysis_project_scope") or session_state.get("active_project_id") or "default-project")
    species_scope = str(session_state.get("analysis_species_scope") or session_state.get("species") or session_state.get("active_project_species") or "all").lower()
    scope_key = f"{user_scope}|{project_scope}|{species_scope}"
    if session_state.get("analysis_settings_scope_key") != scope_key:
        persisted, stamp = load_settings(user_scope, project_scope, species_scope)
        session_state["analysis_settings"] = migrate_settings(persisted or {})
        session_state["analysis_settings_scope_key"] = scope_key
        session_state["analysis_settings_saved_at"] = stamp
        errors, warnings = validate_settings(session_state["analysis_settings"])
        session_state["analysis_settings_validation"] = {"errors": errors, "warnings": warnings}
    return session_state.get("analysis_settings", defaults())


def active_settings_section(session_state, section: str) -> dict:
    """Return a defensive copy of one validated active settings section."""
    cfg = load_active_settings(session_state)
    if section not in cfg or not isinstance(cfg[section], dict):
        raise KeyError(f"Unknown settings section: {section}")
    return copy.deepcopy(cfg[section])


def settings_consumption_matrix(settings=None):
    """Return the central settings-to-engine contract for audit and acceptance tests."""
    from analysis_engine.settings_runtime import settings_consumption_report
    return settings_consumption_report(settings)
