# Release 6.10 — Complete Analysis Settings

## Scope
This release expands the central Analysis & Model Settings page into a versioned configuration layer covering all three implementation phases.

## Configuration domains
1. Study and dataset configuration: species, study design, experimental unit, identifier/group/date/round mappings, methane targets, phenotypic predictors, protocol, instrument, calibration, units and minimum duration.
2. Data quality and preprocessing: imputation, missingness threshold, outlier detection/action, duplicate handling, transformations and scaling.
3. Statistical inference: alpha, confidence level, multiple-testing correction, normality/variance tests, correlations, effect sizes, bootstrap iterations, repeated-measures method, random effects, sphericity and conventional-model assumptions.
4. Machine learning: validation strategy, grouped/temporal split settings, cross-validation, bootstrap, tuning strategy, feature selection, imbalance handling, interpretation and selected estimator hyperparameters.
5. Clustering and dimensionality reduction: algorithms, cluster range, distance, linkage, PCA variance target and UMAP settings.
6. Repeatability: animal/occasion mapping, ICC formulation, confidence level, minimum repeats, random-slope option and within-animal variability summaries.
7. Forecasting: frequency, aggregation, horizon, chronological holdout, model selection, ARIMA/SARIMA orders, seasonality, Prophet flags, SVR and LSTM parameters, rolling-origin option and interval level.
8. Evaluation: regression/classification metrics, residual/autocorrelation diagnostics, model-selection criterion and prediction interval levels.
9. Reporting/reproducibility: export formats, figure formats/resolution, decimal precision, report contents and immutable configuration snapshots.

## Persistence and migration
- Settings remain scoped by user, project and species in the existing SQLite registry.
- Schema version 3 migration fills new settings while retaining recognised values from schema versions 1 and 2.
- Immutable settings snapshots are stored in a separate SQLite `settings_history` table with a SHA-256 configuration fingerprint.
- Analysis pages can load active scoped settings without requiring the user to visit the Settings page first.
- Forecasting controls now use saved forecasting defaults; ML explainability reads the active saved configuration.

## Scientific guardrails
- Warnings identify random validation risk for repeated animal data and seasonal-naïve data sufficiency requirements.
- Settings distinguish ICC/repeatability from heritability.
- MAPE suitability, temporal coverage, missing periods and forecast interpretation are explicitly flagged in the relevant analysis UI.
- Saved settings do not imply every option is already consumed by every analysis engine. Modules must implement and consume a parameter before it changes results; unsupported options remain configuration metadata until wired into that analysis.

## Verification
- Python compilation passed for changed modules/pages.
- Targeted settings/model/forecasting tests: 10 passed, 3 statsmodels convergence warnings.
- Full test suite: 99 passed, 2 failed. Both failures are existing Parquet I/O tests blocked because `pyarrow` is absent from the test environment.
- No live Streamlit browser or deployed-environment test was performed.
