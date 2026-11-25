"""Runtime settings contracts and shared preprocessing for analytical engines.

A setting is considered consumed only when an engine explicitly reads it here or
through an engine adapter. Applicability is method-specific; this module never
forces forecasting or repeated-measures settings into cross-sectional analyses.
"""
from __future__ import annotations
import copy
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, PowerTransformer

# Canonical map: setting path -> engine(s) that are expected to consume it.
SETTING_CONSUMERS = {
    "preprocessing.numeric_imputation": ["preprocessing", "grouped_regression", "nested_grouped_regression"],
    "preprocessing.categorical_imputation": ["preprocessing", "grouped_regression", "nested_grouped_regression"],
    "preprocessing.missing_threshold_pct": ["preprocessing"],
    "preprocessing.outlier_method": ["preprocessing"],
    "preprocessing.outlier_action": ["preprocessing"],
    "preprocessing.outlier_threshold": ["preprocessing"],
    "preprocessing.duplicate_action": ["preprocessing"],
    "preprocessing.transformation": ["preprocessing"],
    "preprocessing.scaling": ["preprocessing", "grouped_regression", "nested_grouped_regression"],
    "statistics.alpha": ["statistical_models", "group_comparison"],
    "statistics.confidence_level": ["statistical_models", "repeatability"],
    "statistics.multiple_testing": ["multiple_testing"],
    "statistics.normality_test": ["diagnostics"],
    "statistics.variance_test": ["diagnostics"],
    "statistics.bootstrap_iterations": ["bootstrap", "repeatability"],
    "statistics.repeated_method": ["repeated_measures"],
    "statistics.random_intercept": ["mixed_models"],
    "statistics.random_slope": ["mixed_models"],
    "statistics.sphericity_correction": ["repeated_measures"],
    "comparison.n_splits": ["grouped_regression", "nested_grouped_regression"],
    "comparison.n_boot": ["bootstrap", "stability"],
    "comparison.random_state": ["all_stochastic_engines"],
    "comparison.test_size": ["holdout_validation"],
    "comparison.validation_strategy": ["model_validation"],
    "comparison.group_column": ["grouped_validation"],
    "comparison.tune_models": ["model_tuning"],
    "comparison.tuning_iter": ["model_tuning"],
    "comparison.tuning_method": ["model_tuning"],
    "comparison.feature_selection": ["feature_selection"],
    "comparison.class_imbalance": ["classification"],
    "comparison.interpretation": ["explainability"],
    "conventional.gee_covariance": ["gee"],
    "conventional.mixed_reml": ["mixed_models"],
    "conventional.quantile": ["quantile_regression"],
    "conventional.spline_n_knots": ["spline_models"],
    "clustering.algorithms": ["clustering"],
    "clustering.min_clusters": ["cluster_diagnostics"],
    "clustering.max_clusters": ["cluster_diagnostics"],
    "clustering.distance": ["hierarchical_clustering"],
    "clustering.linkage": ["hierarchical_clustering"],
    "clustering.pca_variance": ["pca"],
    "clustering.umap_neighbors": ["umap"],
    "clustering.umap_min_dist": ["umap"],
    "repeatability.animal_column": ["repeatability"],
    "repeatability.occasion_column": ["repeatability"],
    "repeatability.icc_type": ["repeatability"],
    "repeatability.confidence_level": ["repeatability"],
    "repeatability.minimum_measurements": ["repeatability"],
    "repeatability.include_random_slope": ["repeatability"],
    "repeatability.within_animal_metrics": ["repeatability"],
    "forecasting.frequency": ["series_preparation"],
    "forecasting.aggregation": ["series_preparation"],
    "forecasting.horizon": ["forecasting"],
    "forecasting.test_fraction": ["forecasting"],
    "forecasting.models": ["forecasting"],
    "forecasting.arima_order": ["arima"],
    "forecasting.sarima_order": ["sarima"],
    "forecasting.seasonal_period": ["seasonal_naive", "sarima"],
    "forecasting.prophet_yearly": ["prophet"],
    "forecasting.prophet_weekly": ["prophet"],
    "forecasting.svr_kernel": ["forecast_svr"],
    "forecasting.svr_c": ["forecast_svr"],
    "forecasting.svr_epsilon": ["forecast_svr"],
    "forecasting.svr_gamma": ["forecast_svr"],
    "forecasting.svr_lags": ["forecast_svr"],
    "forecasting.lstm_lookback": ["lstm"],
    "forecasting.lstm_units": ["lstm"],
    "forecasting.lstm_epochs": ["lstm"],
    "forecasting.lstm_batch_size": ["lstm"],
    "forecasting.lstm_learning_rate": ["lstm"],
    "forecasting.rolling_origin": ["forecast_validation"],
    "forecasting.prediction_interval": ["forecast_intervals"],
    "evaluation.regression_metrics": ["regression_evaluation"],
    "evaluation.classification_metrics": ["classification_evaluation"],
    "evaluation.residual_diagnostics": ["residual_diagnostics"],
    "evaluation.autocorrelation_diagnostics": ["time_series_diagnostics"],
    "evaluation.prediction_intervals": ["prediction_intervals"],
    "evaluation.selection_criterion": ["model_selection"],
    "reporting.formats": ["report_export"],
    "reporting.figure_formats": ["figure_export"],
    "reporting.dpi": ["figure_export"],
    "reporting.decimals": ["report_formatting"],
    "reporting.include_methodology": ["report_export"],
    "reporting.include_parameters": ["report_export"],
    "reporting.include_diagnostics": ["report_export"],
    "reporting.include_dictionary": ["report_export"],
    "reporting.save_versions": ["settings_persistence"],
    "study.name": ["study_metadata"],
    "study.species": ["species_protocol"],
    "study.design": ["study_design"],
    "study.experimental_unit": ["study_design"],
    "study.animal_id": ["grouped_validation", "repeatability", "longitudinal_analysis"],
    "study.group_id": ["grouped_validation", "group_comparison"],
    "study.date_column": ["series_preparation", "longitudinal_analysis"],
    "study.round_column": ["longitudinal_analysis"],
    "study.methane_targets": ["outcome_selection"],
    "study.phenotype_predictors": ["predictor_selection"],
    "study.measurement_unit": ["study_metadata", "report_export"],
    "study.protocol": ["study_metadata", "report_export"],
    "study.instrument": ["study_metadata", "report_export"],
    "study.calibration": ["study_metadata", "report_export"],
    "study.minimum_duration": ["duration_sensitivity"],
    "statistics.correlations": ["correlation_analysis"],
    "statistics.effect_sizes": ["effect_size_analysis"],
    "models.Random Forest": ["random_forest"],
    "models.Extra Trees": ["extra_trees"],
    "models.HistGradientBoosting": ["hist_gradient_boosting"],
    "models.SVR": ["svr"],
    "models.KNN": ["knn"],
    "evaluation.regression_metrics": ["regression_evaluation"],
    "evaluation.classification_metrics": ["classification_evaluation"],
    "reporting.formats": ["report_export"],
}

def get_path(mapping: dict, dotted: str, default=None):
    value = mapping
    for part in dotted.split('.'):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value

def settings_snapshot(settings: dict | None) -> dict:
    return copy.deepcopy(settings or {})

def settings_consumption_report(settings: dict | None = None, consumed: set[str] | None = None) -> pd.DataFrame:
    """Return the explicit settings contract; consumed is runtime evidence supplied by tests."""
    rows=[]
    for path, engines in SETTING_CONSUMERS.items():
        rows.append({"setting":path,"configured":get_path(settings or {},path) is not None,
                     "expected_consumers":", ".join(engines),
                     "runtime_verified":path in (consumed or set())})
    return pd.DataFrame(rows)

def preprocess_frame(df: pd.DataFrame, settings: dict | None = None,
                     columns: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Apply configured data-quality actions to a copy; returns frame and audit log.

    Outlier handling is explicit (flag/cap/remove); the default flag action preserves
    observations. Imputation/scaling are not fitted here because they must be fitted
    inside each training fold for predictive modelling.
    """
    cfg=(settings or {}).get('preprocessing', {})
    out=df.copy(deep=True); cols=list(columns or out.columns)
    numeric=[c for c in cols if c in out and pd.api.types.is_numeric_dtype(out[c])]
    audit={"input_rows":len(out),"dropped_columns":[],"duplicate_rows":0,"outlier_counts":{},"actions":[]}
    threshold=float(cfg.get('missing_threshold_pct',100))
    missing=out[cols].isna().mean()*100
    drop_cols=[c for c in cols if c in missing and missing[c]>threshold]
    audit['dropped_columns']=drop_cols
    if drop_cols:
        out=out.drop(columns=drop_cols); audit['actions'].append('drop_high_missingness_columns')
    dup=out.duplicated().sum(); audit['duplicate_rows']=int(dup)
    duplicate_action=cfg.get('duplicate_action','flag')
    if duplicate_action=='remove' and dup:
        out=out.drop_duplicates().copy(); audit['actions'].append('remove_exact_duplicate_rows')
    method=cfg.get('outlier_method','IQR'); action=cfg.get('outlier_action','flag')
    k=float(cfg.get('outlier_threshold',1.5))
    for col in numeric:
        if col not in out: continue
        x=pd.to_numeric(out[col],errors='coerce')
        if method=='IQR':
            q1,q3=x.quantile(.25),x.quantile(.75); spread=q3-q1
            lo,hi=q1-k*spread,q3+k*spread
        elif method=='zscore':
            mu,sd=x.mean(),x.std(ddof=1); lo,hi=mu-k*sd,mu+k*sd
        else:
            continue
        mask=(x<lo)|(x>hi); n=int(mask.sum()); audit['outlier_counts'][col]=n
        if n and action=='cap': out[col]=x.clip(lo,hi); audit['actions'].append(f'cap:{col}')
        elif n and action=='remove': out=out.loc[~mask].copy(); audit['actions'].append(f'remove_outliers:{col}')
        elif n and action=='flag': out[f'{col}__outlier_flag']=mask.astype('int8')
    transform=cfg.get('transformation','none')
    for col in numeric:
        if col not in out: continue
        x=pd.to_numeric(out[col],errors='coerce')
        if transform=='log1p':
            if (x.dropna() < 0).any(): raise ValueError(f"log1p transformation requires non-negative values: {col}")
            out[col]=np.log1p(x)
        elif transform=='yeo_johnson':
            valid=x.notna()
            if valid.sum()>2: out.loc[valid,col]=PowerTransformer(method='yeo-johnson').fit_transform(x.loc[valid].to_numpy().reshape(-1,1)).ravel()
    audit['output_rows']=len(out); audit['output_columns']=len(out.columns)
    return out,audit
