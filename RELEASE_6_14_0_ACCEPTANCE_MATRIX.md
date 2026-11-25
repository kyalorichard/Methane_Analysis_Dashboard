# Release 6.14.0 Acceptance Matrix

| Requirement | Status | Evidence |
|---|---|---|
| Settings propagation in selected ML, PCA/clustering and forecasting workflows | Implemented for the listed integrations | Engine-level parameter-behaviour tests |
| All applicable settings consumed by all engines | Partial / not yet accepted | Full setting-to-engine runtime trace and perturbation tests outstanding |
| Shared service dispatch for selected analytical pages | Implemented for migrated pages | Registry dispatch used by ML, clustering/PCA, forecasting and scientific workbench |
| Complete removal of duplicated analytical implementations | Partial / not yet accepted | Exact duplicate AST scan found none; semantic overlap audit and migration remain outstanding |
| Python compilation | Passed | `compileall` |
| Automated regression tests | 121 passed, 9 warnings | Parquet tests excluded because pyarrow is unavailable |
| Live Streamlit, cloud database and multi-user deployment tests | Pending | Not run in this environment |
