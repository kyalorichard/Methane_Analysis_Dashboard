# Release 6.15.0 – Analytical Engine Consolidation

## Scope of this update

This release continues the 6.14.0 refactor by consolidating the two quantile-regression implementations behind one canonical estimator.

- `analysis_engine.advanced.fit_quantile_regression` is the canonical implementation.
- `analysis_engine.advanced_research.fit_quantile_regression` is now a compatibility adapter. It delegates to the canonical implementation and preserves the historical `(model, used_data)` return contract.
- The Scientific Analysis Workbench and Advanced Inference pages now route quantile regression through the shared service registry / canonical engine.
- The quantile setting `conventional.quantile` is consumed when a caller does not explicitly override the quantile in the analysis UI.
- Explicit user-selected quantiles continue to take precedence over the saved default.

## Scientific distinctions retained

The following methods are not collapsed merely because their names or broad purpose overlap:

- `statistics.fit_mixedlm` and `research_hardening.fit_mixed_effects`: the latter supports an optional random time slope and session-specific model structure; they are not interchangeable estimators.
- `advanced.repeatability_icc` and `release6.estimate_repeatability_icc`: long-format one-way random-effects repeatability and balanced-panel ICC formulations have different assumptions and estimands.
- `advanced.fit_allometry` and `advanced_research.fit_allometric_scaling`: the former permits covariate adjustment; the latter is a simple two-variable log-log scaling model.
- `research_hardening.grouped_classification_benchmark` and `classification_validation.grouped_nested_classification`: basic grouped benchmarking and nested/calibrated classification validation have different validation scopes.

## Verification

- Python compilation: passed.
- Regression tests excluding `tests/test_dataset_formats.py`: 121 passed before this release's two additional tests.
- Added canonical-engine adapter tests for output equivalence and configured quantile consumption.
- Parquet tests remain unrun in this environment because `pyarrow` is unavailable.

## Completion status

This release removes one confirmed duplicated analytical implementation. It does **not** certify complete removal of all semantic duplication or complete runtime consumption of every settings parameter. Those require further page-by-page parameter wiring and method-specific integration tests. The exact-AST duplicate audit is not treated as proof of semantic uniqueness.

No live Streamlit browser, production database, object-storage, or deployment validation is claimed.
