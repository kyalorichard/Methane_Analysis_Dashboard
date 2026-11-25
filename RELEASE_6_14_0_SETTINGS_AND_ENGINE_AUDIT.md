# Release 6.14.0 — Settings and Analytical Engine Audit Update

## Implemented in this package
- Nested animal-grouped ML benchmarking now receives the active settings object from the dashboard page.
- PCA consumes the configured explained-variance threshold.
- Cluster-number diagnostics consume configured minimum/maximum cluster counts and the project random seed.
- Clustering comparison consumes the configured algorithm list (when no explicit list is passed), cluster count, distance metric, linkage and random seed. Ward linkage is guarded to Euclidean distance.
- Forecasting uses the configured model list when the caller does not explicitly supply one.
- SARIMA uses the non-seasonal `(p,d,q)` values from the configured SARIMA order, rather than accidentally reusing the ARIMA order.
- The ML benchmarking, clustering/PCA, forecasting and scientific workbench pages now dispatch selected calculations through the shared service registry.
- Added parameter-behaviour regression tests for PCA variance, cluster range, clustering distance/linkage and forecasting model selection.
- Added static settings-reference and exact-function-body duplicate audit utilities, with machine-readable reports under `reports/`.

## Verification
- Python compilation: passed.
- `PYTHONPATH=. pytest -q --ignore=tests/test_dataset_formats.py`: **121 passed, 9 warnings**.
- Parquet-specific tests remain excluded because `pyarrow` is not installed in this execution environment.
- Exact AST-body duplicate scan: 0 exact duplicate top-level function bodies across `analysis_engine/` and `pages/` (153 unique function bodies scanned).

## Acceptance status — important
This release is a substantive refactoring and audit update. It does **not** claim that every applicable setting is now consumed by every engine, or that all semantically duplicated analytical implementations have been removed.

The settings reference report is static evidence only: a source reference does not prove that a setting changes a computation. Complete acceptance still requires a runtime consumer test for every applicable setting in `settings_config.defaults()`, with explicit not-applicable designations where appropriate.

The exact AST duplicate scan detects only identical function bodies. It cannot establish the absence of semantic duplication where implementations have different names, structures, assumptions or estimands. The long-format and balanced-panel repeatability estimators, for example, remain separate intentionally.

## Remaining work before both requirements can be marked complete
1. Complete a setting-to-engine trace for every page and every setting in `settings_config.defaults()`.
2. Add parameter perturbation tests for every applicable setting; document genuine non-applicability.
3. Complete a semantic overlap audit across all 38 analytical pages and engine modules.
4. Move duplicate calculations to canonical implementations, preserving different estimands and validation assumptions.
5. Remove superseded implementations only after equivalence tests pass.
6. Run all tests including Parquet tests in an environment with `pyarrow`, then perform Streamlit UI, multi-user, database and deployment validation.

## Scientific safeguards
- Predictive preprocessing must be fitted inside training folds to avoid leakage.
- Grouped validation must keep all records from the same animal/group together.
- Balanced-panel and unbalanced long-format repeatability estimators must not be conflated.
- Time-series gaps must not be collapsed into consecutive observations.
- Significance thresholds, confidence intervals and effect-size estimands must remain explicit.
