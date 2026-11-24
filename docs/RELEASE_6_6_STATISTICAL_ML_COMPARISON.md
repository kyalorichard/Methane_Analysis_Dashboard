# Release 6.6 — Matched conventional statistics versus machine learning

## Purpose

This release upgrades the narrow OLS-versus-one-ML comparison into a matched grouped cross-validation framework. Every selected model receives the same outer GroupKFold partitions, target, predictor set and held-out groups. Preprocessing is fitted inside each training fold to prevent leakage.

## Supported model families

### Conventional statistical models
- OLS linear regression (predictive baseline; robust inferential OLS remains available in the statistical modelling workflow).
- GEE with exchangeable working correlation; predictions are marginal population-level predictions.
- Random-intercept linear mixed-effects model; held-out predictions use the fixed-effects component because test groups are unseen.
- Spline regression using cubic B-spline basis functions (GAM-like smooth predictive baseline; not a full penalized GAM inference implementation).
- Median quantile regression.
- Allometric power-law regression, available only with exactly one positive numeric predictor and positive outcome. Log-scale fitting uses a training-fold smearing correction for retransformation.

### Machine-learning models
- Random Forest, Extra Trees, HistGradientBoosting, SVR and KNN.

## Outputs

- Out-of-fold RMSE, MAE, R², mean prediction bias and median absolute error.
- Model family, completed folds, sample/group counts and elapsed fit/predict time.
- Paired group-bootstrap confidence intervals for RMSE differences between each pair of successfully evaluated models.
- Downloadable model metrics, paired comparisons and row-level out-of-fold predictions.

## Scientific interpretation

This is a predictive comparison, not a comparison of causal estimands, coefficient inference or biological mechanisms. GEE and mixed-effects models have different dependence assumptions and population/conditional interpretations. Mixed-effects predictions for unseen groups use fixed effects only. Spline regression is a spline-basis regression comparator, not a complete GAM framework with smoothing-parameter inference. Allometric regression requires a scientifically justified positive predictor (typically body weight) and positive target. Group-bootstrap intervals are only defensible when the selected grouping variable represents the independent sampling unit.

A positive RMSE difference defined as RMSE(A) minus RMSE(B) favours B; a negative difference favours A. Intervals crossing zero do not provide strong evidence of a difference at the corresponding nominal confidence level. The percentile interval is descriptive and is not adjusted for multiple pairwise comparisons.

## Validation

The new tests use synthetic repeated-measures data to verify matched out-of-fold predictions, pairwise bootstrap output, insufficient-group safeguards and allometric model eligibility. Mixed-effects and GEE execution was additionally smoke-tested on repeated synthetic data. Full browser-based Streamlit testing remains necessary in the user's deployment environment.
