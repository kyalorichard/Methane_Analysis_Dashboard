# Release 6.13.0 Acceptance Matrix

| Requirement | Status in 6.13.0 | Evidence / remaining work |
|---|---|---|
| Shared settings-to-engine contract | Implemented | `analysis_engine/settings_runtime.py` |
| Shared opt-in preprocessing | Implemented | Outlier, missingness, duplicate, transform tests |
| Nested grouped-CV settings | Implemented | `analysis_engine/ml.py`; verify with full ML regression tests |
| Forecasting settings integration | Implemented for listed model parameters | `time_series_forecasting.py`; optional Prophet/PyTorch tests depend on installed packages |
| Conventional model adapters in registry | Implemented | OLS, GEE, MixedLM adapters |
| All Settings parameters consumed by all applicable engines | Partial | Contract identifies consumers; remaining page/engine wiring and per-setting effect tests required |
| Complete removal of duplicated analytical implementations | Partial | Registry expanded; page-by-page migration and numerical equivalence tests required |
| Production deployment certification | Not tested | Browser, PostgreSQL/S3, identity isolation and production startup tests required |
