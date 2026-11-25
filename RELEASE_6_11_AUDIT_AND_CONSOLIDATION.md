# Release 6.11.0 — Platform Consistency and Integration Foundation

## Scope
This release begins the consolidation programme against the supplied Release 6.10.1 source archive. It is a compatibility-preserving foundation release, not a claim that every analytical page has already been refactored or browser-validated.

## Changes
- Corrected the internal release marker to `6.11.0`.
- Added `platform_core.storage` as the single backend-selection facade for project and dataset operations.
- Refactored the Project Workspace page to use the facade instead of selecting and importing backend functions independently.
- Refactored shared sidebar project selection to use the same facade. Local projects can now be selected in the shared navigation when local storage is active.
- Refactored project archive import/export to use the selected storage backend rather than hard-coding PostgreSQL/S3 functions.
- Changed project-scoped settings/archive state keys from mutable project names to stable project IDs in the workspace flow.
- Set the authenticated principal subject in the landing-page session state so scoped settings can resolve a stable user identity.
- Added storage-facade regression tests.

## Audit findings retained for follow-up
- There are 38 Streamlit pages, 28 analysis-engine modules, 9 platform-core modules and 25 test modules in the supplied source.
- Storage operations had duplicated implementations in `platform_core.workspace` and `platform_core.local_workspace`; the facade now centralises backend selection, while backend-specific implementations remain intentionally separate.
- Analysis settings are not yet consumed by every analytical page. Only the advanced ML explainability and forecasting pages explicitly load the shared configuration at this point. Further module-by-module integration is required.
- Several page groups have overlapping user-facing purposes. The audit recommends shared services and a simplified workflow, but does not delete specialist pages in this foundation release.
- `analysis_engine.experiment_registry`, `platform_core.run_registry`, and project workspace metadata remain separate persistence stores. A unified run/experiment schema requires a migration plan and must not be attempted by silently merging or deleting existing data.
- Local storage is single-instance SQLite/filesystem storage. Multi-user deployment requires persistent storage and the intended authentication/tenant configuration; it is not equivalent to the PostgreSQL/S3 multi-tenant backend.

## Verification
- Python compilation: passed for app, pages, analysis_engine and platform_core.
- Full pytest suite: 101 passed, 2 failed, 13 warnings in the audit environment.
- The two failures are Parquet tests blocked because `pyarrow` is not installed in the audit runtime. `pyarrow>=15` is declared in `requirements.txt`.
- Streamlit browser, cloud deployment, authentication proxy, PostgreSQL and S3 integration were not exercised in this environment.

## Deployment notes
- Preserve Streamlit secrets and environment variables.
- For local mode, set `PROJECT_STORAGE_BACKEND=local` and mount a persistent volume at `LOCAL_PROJECT_STORAGE_DIR`.
- For cloud mode, configure both `DATABASE_URL` and `S3_BUCKET`, then set `PROJECT_STORAGE_BACKEND=cloud`.
- Back up existing SQLite files and project data before deployment.
