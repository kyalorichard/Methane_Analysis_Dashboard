"""Canonical dispatch registry for shared scientific computations.

UI pages own interaction and visualisation; computations belong in these services.
Methods with different estimands (e.g. balanced-panel versus long-format ICC)
remain distinct and are named explicitly to prevent accidental substitution.
"""
from __future__ import annotations

SERVICE_MAP = {
    "preprocess_frame": ("analysis_engine.settings_runtime", "preprocess_frame"),
    "settings_consumption_report": ("analysis_engine.settings_runtime", "settings_consumption_report"),
    "fit_ols": ("analysis_engine.statistics", "fit_ols"),
    "fit_gee": ("analysis_engine.statistics", "fit_gee"),
    "fit_mixedlm": ("analysis_engine.statistics", "fit_mixedlm"),
    "grouped_regression": ("analysis_engine.ml", "grouped_regression_benchmark"),
    "nested_grouped_regression": ("analysis_engine.ml", "nested_grouped_regression_benchmark"),
    "configured_estimator": ("analysis_engine.ml", "configured_estimator"),
    "grouped_model_comparison": ("analysis_engine.model_comparison", "compare_grouped_models"),
    "pca_scores": ("analysis_engine.unsupervised", "pca_scores"),
    "animal_profiles": ("analysis_engine.unsupervised", "animal_profiles"),
    "cluster_diagnostics": ("analysis_engine.unsupervised", "cluster_diagnostics"),
    "compare_clusterers": ("analysis_engine.unsupervised", "compare_clusterers"),
    "group_comparison": ("analysis_engine.advanced", "group_comparison"),
    "bootstrap_icc": ("analysis_engine.reliability", "bootstrap_long_format_icc1"),
    "bland_altman": ("analysis_engine.advanced", "bland_altman"),
    "fit_allometry": ("analysis_engine.advanced", "fit_allometry"),
    "fit_quantile_regression": ("analysis_engine.advanced", "fit_quantile_regression"),
    "duration_sensitivity": ("analysis_engine.advanced", "duration_sensitivity"),
    "tost_independent": ("analysis_engine.advanced", "tost_independent"),
    "cluster_stability": ("analysis_engine.advanced", "cluster_stability"),
    "repeatability_long_format": ("analysis_engine.reliability", "estimate_long_format_icc1"),
    "repeatability_balanced_panel": ("analysis_engine.reliability", "estimate_balanced_panel_icc"),
    "build_reliability_panel": ("analysis_engine.reliability", "build_subject_occasion_panel"),
    "within_between_variability": ("analysis_engine.reliability", "within_between_variability"),
    "bland_altman_paired": ("analysis_engine.reliability", "bland_altman_paired"),
    "phenotype_validation": ("analysis_engine.phenotype_validation", "distribution_diagnostics"),
    "phenotype_evidence": ("analysis_engine.research_intelligence", "phenotype_evidence_matrix"),
    "prepare_forecast_series": ("analysis_engine.time_series_forecasting", "prepare_series"),
    "compare_forecasters": ("analysis_engine.time_series_forecasting", "compare_forecasters"),
    "report_bundle": ("analysis_engine.standalone_pipeline", "build_analysis_bundle"),
}

def get_service(name: str):
    import importlib
    if name not in SERVICE_MAP:
        raise KeyError(f"Unknown analysis service: {name}")
    module_name, attr = SERVICE_MAP[name]
    return getattr(importlib.import_module(module_name), attr)

def service_names():
    return tuple(sorted(SERVICE_MAP))
