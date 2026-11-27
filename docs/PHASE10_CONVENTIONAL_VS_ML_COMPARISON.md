# Phase 10 — Conventional vs Machine Learning Comparison

## New dedicated workspace

`pages/38_Conventional_vs_ML_Comparison.py` provides a dedicated workflow for comparing conventional statistical regression models and machine-learning regressors on a common predictive task.

### Model families

- Conventional: OLS, GEE with exchangeable correlation, random-intercept mixed-effects model, spline regression, median quantile regression, and allometric power-law regression.
- Machine learning: Random Forest, Extra Trees, HistGradientBoosting, SVR, and KNN.

### Validation and outputs

- Uses the shared `analysis_engine.model_comparison.compare_grouped_models` engine.
- All selected models use the same GroupKFold partitions and predictor set.
- Imputation, encoding and scaling are fitted within each training fold.
- Requires at least five independent groups and recommends grouping at the highest independent sampling unit (animal, herd, farm, or site as appropriate).
- Reports out-of-fold RMSE, MAE, R², mean prediction bias, median absolute error, model runtime, completion status and warnings.
- Reports paired group-bootstrap confidence intervals for RMSE differences.
- Provides observed-versus-predicted and residual plots, plus CSV exports for metrics, pairwise comparisons and out-of-fold predictions.
- Optional ML hyperparameter tuning is nested within each outer training fold.

## Navigation changes

- Added the new workspace to the Machine Learning navigation section.
- Added direct links from Statistical Models, ML Benchmarking and the Unified Research Model Lab.
- Replaced the embedded comparison block in page 34 with a link to the dedicated page, avoiding two separate comparison interfaces.

## Interpretation caveats

The workspace compares predictive performance; it does not make inferential estimands interchangeable. OLS, GEE and mixed-effects models have different assumptions and interpretations. Predictive scores do not establish causality or biological mechanism. Grouped validation is only as independent as the selected grouping unit.

## Validation

- Python compilation passed.
- Existing model-comparison service tests passed as part of the full test suite.
- Full available test suite: see release notes; dataset-format tests requiring PyArrow are excluded if the audit environment lacks that dependency.
- Streamlit browser interaction, authentication, live database/storage integrations and cloud deployment are not tested by the local test suite.
