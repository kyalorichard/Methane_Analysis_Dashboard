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
    "animal_profiles": ("analysis_engine.unsupervised", "animal_profiles"),
    "pca_scores": ("analysis_engine.unsupervised", "pca_scores"),
    "cluster_diagnostics": ("analysis_engine.unsupervised", "cluster_diagnostics"),
    "compare_clusterers": ("analysis_engine.unsupervised", "compare_clusterers"),
    "repeatability_long_format": ("analysis_engine.advanced", "repeatability_icc"),
    "repeatability_balanced_panel": ("analysis_engine.release6", "estimate_repeatability_icc"),
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
