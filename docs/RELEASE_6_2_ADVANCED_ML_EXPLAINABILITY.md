# Release 6.2 — Advanced ML validation and explainable AI

## Scope
Release 6.2 adds a consolidated Streamlit workflow at `pages/34_Advanced_ML_Explainability.py` and links it from the application navigation.

## Integrated capabilities
- Group-aware learning curves using the existing `grouped_learning_curve` engine function.
- Group-bootstrap feature-selection stability for numeric predictors and tree estimators.
- Optional SHAP explanations for a fitted preprocessing/model pipeline. SHAP remains an optional dependency; the page reports a clear installation message if it is absent. Explanations are computed on a held-out animal-grouped sample with a bounded background sample.
- Group-split conformal regression intervals, separating model-fit groups, calibration groups and test groups.
- Conventional OLS baseline versus a selected ML estimator using identical GroupKFold partitions and predictors.
- Frozen-model regression validation on an independently uploaded CSV/Parquet cohort.
- Integrated animal-grouped classification benchmarking and confusion matrices using the existing classifier engine.

## Scientific safeguards and boundaries
- Grouping must reflect the highest independent sampling unit. Animal grouping is insufficient if animals are clustered by farm, herd, site or study and the intended inference is to new farms/herds/sites.
- Feature importance and SHAP describe model reliance, not causal effects. Correlated predictors can distribute attribution across variables.
- The current feature-selection stability workflow requires numeric predictors and estimators exposing aligned tree impurity importances. It is a screening procedure, not a complete wrapper/embedded feature-selection comparison.
- Conformal coverage is marginal and relies on exchangeability of independent groups. Distribution shift, protocol differences and dependence above the selected group level can invalidate nominal coverage.
- External validation does not refit the estimator. Researchers must verify cohort independence, predictor harmonisation, units, measurement protocol and outcome definition.
- The classification workflow reports grouped hard-label metrics and confusion matrices. Nested group-aware probability recalibration, full out-of-fold probability calibration curves and class-conditional uncertainty remain outstanding.
- The OLS-versus-ML comparison is predictive. It does not compare causal estimands or make inferential p-values equivalent to predictive performance.

## Validation
The release is validated with automated unit tests and Python compilation. The available environment run produced 65 passing tests and 2 failures in Parquet-format tests because `pyarrow` is absent from the build environment, although `pyarrow>=15` is declared in `requirements.txt`. Excluding those environment-dependent Parquet tests, 63 tests pass. A Streamlit browser-based end-to-end test and production-scale performance/security test are not included. SHAP execution requires the optional `shap` package and was not assumed available in the base environment.

## Requirement status after Release 6.2

| Requirement | Status | Current position / remaining work |
|---|---|---|
| Regression model benchmarking | Implemented | Existing grouped regression model suite retained; broader nested benchmarking remains the preferred estimate. |
| Classification model benchmarking | Partial | Grouped classifier benchmarking and confusion matrices integrated. Probability-based OOF metrics, calibration and nested tuning across classifiers remain. |
| Nested grouped cross-validation | Implemented for regression | Inner tuning and outer evaluation are available for regression. A unified nested workflow across classifier families and additional grouping levels remains. |
| Hyperparameter optimization | Implemented for regression | Nested regression tuning integrated. Broader configurable search spaces, compute controls and classifier tuning remain. |
| SHAP explainability | Partial | Optional SHAP workflow now integrated for a held-out animal-grouped sample. Add optional dependency, validate on representative datasets, extend to classification and interaction/dependence plots, and record SHAP background/provenance for publication. |
| Feature selection stability | Implemented (numeric/tree scope) | Group-bootstrap selection frequency available for numeric predictors and tree estimators. Generalized stability selection for mixed predictors, correlated-feature groups and multiple selection methods remains. |
| Model calibration | Partial | Existing regression calibration diagnostics and grouped classification hard-label metrics retained. Group-aware probability calibration, OOF reliability curves, calibration slope/intercept and Brier score workflows remain. |
| Prediction uncertainty | Partial | Group-split conformal regression intervals added. Repeated group-level coverage assessment, conditional/heteroscedastic intervals, classification uncertainty and external validation remain. |
| Learning curves | Implemented | Group-aware regression learning curves integrated. Classification learning curves and more explicit group-count-based learning-curve reporting remain. |
| Residual diagnostics | Implemented | Held-out regression residual diagnostics retained. More comprehensive fold-wise residual checks and automated assumption flags remain. |
| Conventional statistics versus ML comparisons | Partial | OLS predictive baseline versus ML now uses identical grouped folds. A broader comparison of mixed models/GAMs/quantile/allometric methods, estimands, uncertainty and inferential diagnostics remains. |
| External validation framework | Partial | Frozen regression model evaluation on an uploaded external cohort integrated. Classification external validation, multi-cohort harmonisation, subgroup transportability, domain shift and a formal validation protocol remain. |

## Outstanding Release 6.3+ work
1. Complete grouped probability calibration for classifiers, including out-of-fold probabilities, reliability diagrams, Brier score, calibration intercept/slope and group-aware recalibration without leakage.
2. Extend nested grouped tuning to classification and to explicit herd/farm/site/study grouping configurations.
3. Add a formal external-validation protocol with frozen preprocessing/model artefacts, schema and unit checks, protocol harmonisation, subgroup metrics, domain-shift diagnostics and a validation report.
4. Expand prediction uncertainty to repeated group-level coverage studies, conditional intervals and classification uncertainty; assess performance under temporal and geographic shift.
5. Expand SHAP to classification, class-specific explanations, dependence/interaction views, robust background selection and explainability provenance.
6. Extend feature-selection stability to mixed data, correlated feature families and multiple selection algorithms; quantify uncertainty in selection frequencies.
7. Add fold-wise residual diagnostics and a standardised statistical-versus-ML comparison across mixed-effects, GAM, quantile and allometric models where assumptions and estimands are compatible.
8. Conduct browser-based UI testing, representative dataset testing, runtime profiling, security review and production deployment validation.
