# Release 6.13.0 – Settings Runtime and Analytical Service Consolidation

## Implemented in this update

- Added `analysis_engine.settings_runtime` with a central settings-to-engine contract, audit report, and shared preprocessing implementation.
- Added configurable missingness-column handling, duplicate handling, IQR/z-score outlier flagging/capping/removal, and none/log1p/Yeo–Johnson transformations. The default outlier action remains `flag`; no observations are silently discarded.
- Expanded the service registry to expose shared preprocessing, conventional statistical models, ML estimators, clustering/PCA, repeatability, forecasting, validation, and reporting services.
- Added settings-aware nested grouped CV: fold count, seed, imputation, scaling, tuning method and tuning iteration budget are now read from active settings.
- Extended forecasting engine configuration to consume stored horizon, holdout fraction, model list, ARIMA/SARIMA orders, seasonal period, Prophet seasonality, SVR hyperparameters, LSTM lookback/units/epochs/batch size/learning rate, and random seed. The forecasting page now passes the active settings to the engine.
- Added settings runtime tests for preprocessing actions, settings contract, and service registry resolution.

## Important implementation boundaries

This release establishes and tests shared runtime contracts and integrates the highest-impact ML and forecasting pathways. It does **not** establish that every control in every page is fully consumed. The settings contract lists expected consumers; `runtime_verified` remains false until an engine-level test or explicit instrumentation demonstrates consumption. Settings that are not yet wired must not be reported as complete.

The service registry is the canonical dispatch surface, but a registry entry alone does not prove that all historical page-level duplicated code has been removed. A full page-by-page migration and equivalence review remains necessary before declaring complete deduplication.

The generic preprocessing service is opt-in. It is deliberately not automatically applied globally by `get_data()`, because silently transforming source data could invalidate existing analyses and break reproducibility. Predictive preprocessing must continue to be fitted within training folds to prevent leakage.

## Scientific safeguards

- Outlier flagging is the default and preserves records.
- Outlier removal/capping and transformations are explicit and auditable.
- Forecast validation remains chronological; no random shuffling is introduced.
- Prophet, PyTorch, and other optional dependencies remain optional.
- Long-format and balanced-panel repeatability estimators remain separate because their assumptions and estimands differ.

## Verification status

Run `python -m compileall -q app.py api analysis_engine platform_core pages worker` and `PYTHONPATH=. pytest -q --ignore=tests/test_dataset_formats.py`.

This package must not be treated as production-certified until the complete regression suite, browser workflow, cloud PostgreSQL/S3, multi-user isolation, and empirical methane dataset validation are completed in the target deployment environment.
