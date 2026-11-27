# Phase 8 — Shared analytical services and workflow consolidation

**Release:** 27 November 2026  
**Base:** Phase 7 QC Winsorization

## Scope delivered

1. **Canonical data provenance:** added `analysis_engine/data_provenance.py`; QC, research intelligence, integrated analysis, standalone analysis bundles, publication reports, scientific reports, ML metadata and quick exports now use the same dataframe SHA-256 fingerprint implementation.
2. **Central QC services:** moved row-level non-destructive QC flagging and configured-range summaries into `analysis_engine/quality_control.py`. `research_intelligence.flag_data_quality` and `research_hardening.configurable_qc` remain compatibility adapters. Research Intelligence now links to the central QC Centre rather than exposing a second QC decision queue.
3. **Canonical mixed-effects fitting:** added `analysis_engine/mixed_models.py` with random-intercept fitting, optimizer fallback and convergence/small-group diagnostics. The conventional statistics adapter, Research Model Lab adapter and advanced-research adapter now share this implementation. Random-slope and longitudinal mixed models remain distinct.
4. **Emitter-tail consolidation:** added `analysis_engine/emitter_thresholds.py`; static emitter cohort assignment and round-specific emitter tracking now share one percentile/rank assignment helper while retaining their different observational units.
5. **Allometric model consolidation:** `advanced_research.fit_allometric_scaling` now adapts the canonical `advanced.fit_allometry` implementation while preserving its established result dictionary.
6. **Service registry:** expanded `service_registry.py` to register provenance, QC, mixed-effects, grouped-classification and report-generation services.
7. **Navigation:** the advanced ML workspace is the primary Model Lab entry. Regression benchmarking, the original classification/mixed-model page, variable importance, quick exports and trajectory-only view remain accessible under Specialist Workflows. No page files or scientific methods were deleted.
8. **Publication outputs:** publication bundles and scientific reports remain separate output profiles but are now exposed through the shared service registry and share the same fingerprint algorithm.

## Scientific methods deliberately retained

- Balanced-panel ICC(1/2/3) and unbalanced long-format ICC(1,1) remain separate estimands.
- Bland–Altman paired-method agreement and reference-based calibration diagnostics remain distinct workflows.
- Random-intercept, random-slope and longitudinal mixed-effects models remain distinct covariance structures.
- Basic grouped classification and nested grouped classification remain separate validation designs.
- Static emitter cohort classification and round-specific emitter tracking remain separate analyses.
- Bootstrap clustering stability and consensus clustering remain separate robustness methods.

## Compatibility

Legacy function names and return contracts are retained where existing pages/tests depend on them. The adapters should be removed only after all callers and saved workflows have migrated.

## Validation

- Python compilation: passed.
- `pytest -q --ignore=tests/test_dataset_formats.py`: **194 passed**.
- Dataset-format tests: 2 passed and 2 Parquet tests could not run successfully because `pyarrow` is not installed in this audit environment. `requirements.txt` already declares `pyarrow>=15`; rerun these two tests in the deployment environment after installing requirements.
- Tests report expected numerical/model convergence warnings in random-slope and forecasting fixtures; a passing test does not imply convergence for every dataset.
- No production Streamlit Cloud deployment, live authentication, PostgreSQL, S3 or browser smoke test was performed.

## Follow-up

A subsequent release should migrate the remaining page-level analysis controls to the service registry, introduce typed result schemas, and retire compatibility adapters only after method-parity tests and production smoke testing.
