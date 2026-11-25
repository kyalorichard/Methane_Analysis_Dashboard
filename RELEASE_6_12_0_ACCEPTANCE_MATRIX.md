# Release 6.12.0 — Acceptance matrix

| Workstream | Implemented in source | Automated evidence | Live deployment evidence | Status |
|---|---|---|---|---|
| Shared storage facade | Backend selection centralised | Existing storage facade tests | Not available | Partial |
| Shared analysis context | Common context resolver and `get_data()` integration | New context regression test | Not available | Implemented in source |
| Unified local metadata DB | Opt-in via `METHANE_METADATA_DB`; legacy overrides take precedence | New cross-registry SQLite integration test | Not available | Implemented; migration required |
| Central settings | Loaded into shared context; several engine integrations | Settings and page compilation tests | Not available | Partial |
| Active data lifecycle | Project switch invalidation retained; dataset fingerprint added | Existing project tests and context test | Not available | Partial |
| Analytics consolidation | Specialist engines retained; no destructive page removals | Module-specific tests | Not available | Partial |
| Navigation | All 38 page scripts linked; no orphaned page scripts | Static target audit | Not available | Implemented in source |
| Forecast time integrity | Missing bins preserved; training-only imputation; observed count validated | New gap-preservation test | Not available | Implemented in source |
| Full dependency/deployment acceptance | `pyarrow` declared in requirements | 111 tests pass outside Parquet test module | Streamlit Cloud/browser/Postgres/S3 not tested | Outstanding |

## Test result in this build environment
- Targeted integration suite: 14 passed, 3 statsmodels convergence warnings.
- Full suite: 111 passed, 2 failed because `pyarrow` is not installed in this execution environment.
- Python compilation: passed.
- Static navigation audit: 38 page scripts, 38 navigation targets, zero orphaned pages.

## Explicitly not certified
No claim is made that every Settings parameter is applied to every analytical engine, all related workflows have been fully consolidated, legacy metadata has been migrated, or the cloud deployment has passed acceptance. These require additional page-by-page integration and a live deployment environment.
