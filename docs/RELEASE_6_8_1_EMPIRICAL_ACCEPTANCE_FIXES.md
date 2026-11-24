# Release 6.8.1 — Empirical acceptance fixes

## Scope
This patch follows an empirical acceptance test using the ICARDA sheep methane phenotype dataset (1,740 monitoring records, 595 animals, 32 variables). The raw dataset is not bundled in this release archive.

## Corrections
- Formula-based GEE and mixed-effects comparators now impute numeric and categorical predictors from each outer-training fold only, then apply those values to the held-out fold.
- Unseen categorical levels in a held-out fold are mapped to the training-fold mode for formula-based statsmodels prediction. This avoids Patsy design-matrix failures without using held-out outcomes.
- Training and test fold indices are reset before fitting/prediction, preventing statsmodels index-alignment errors.
- Mixed-effects optimization now also tries Nelder–Mead (`nm`) after the existing optimizers.
- Held-out predictions are checked for correct length and finite values; incomplete predictions produce an explicit failed-model status instead of an empty warning field.
- Added a regression test covering missing categorical values and held-out category levels for GEE and mixed-effects comparisons.

## Empirical verification
On the sheep dataset, OLS, spline regression, median quantile regression, GEE, random-intercept mixed-effects, Random Forest, Extra Trees, HistGradientBoosting, SVR and KNN all completed five animal-grouped folds. The empirical comparison used `AnimalID` as the grouping unit and a common predictor set of animal, site, programme and measurement-context variables.

## Validation
- Python compilation passed.
- 88 tests passed when the two Parquet tests requiring the unavailable `pyarrow` runtime dependency were deselected.
- Full suite: 88 passed, 2 failed because `pyarrow` was not installed in the build environment; it is declared in the project requirements.
- Six pre-existing numerical/convergence warnings remain in unrelated tests.
- Browser-based Streamlit end-to-end testing remains pending in an environment with Streamlit installed.

## Scientific interpretation boundary
The comparison is predictive, not causal. The mixed-effects model's held-out predictions for unseen animals use fixed effects only. The empirical dataset has only seven animals observed in both R1 and R2, limiting round-to-round longitudinal inference. LMD concentration/AUC-derived phenotypes are not methane mass flux without validated calibration.
