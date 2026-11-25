# Release 6.12.1 acceptance matrix

| Requirement | Implementation in source | Automated evidence | Status |
|---|---|---|---|
| Shared active analysis context | Context resolver called by shared `get_data()` | `test_analysis_context.py` | Implemented for pages using shared loader |
| Model/preprocessing settings consumption | Grouped regression consumes imputation, scaling, model hyperparameters and seed | `test_settings_consumption.py` | Passed |
| Settings across all analytical pages | Existing page-specific integrations retained; universal settings UI-to-engine mapping not exhaustive | Static source review only | Partial; do not mark every setting complete |
| Shared scientific service entry point | `analysis_engine.service_registry` maps canonical service names | Compilation and import checks | Implemented as dispatch layer |
| Removal of all duplicate page logic | Specialist pages retained; not destructively merged | No full semantic equivalence audit | Partial; methods with different estimands remain distinct |
| Legacy local SQLite metadata migration | Workspace, settings/experiments, and run registry paths copied into canonical DB | `test_metadata_auto_migration.py`, `test_unified_metadata_store.py` | Passed for tested SQLite schemas |
| Source preservation | Timestamped SQLite backups; legacy DBs not deleted | Migration test | Passed |
| Migration idempotence | Migration source paths recorded | Migration test | Passed |
| Full test suite | 112 tests pass excluding Parquet test module | `pytest -q --ignore=tests/test_dataset_formats.py` | Passed with 9 warnings |
| Parquet tests | Requires pyarrow runtime | Not run here | Pending environment dependency |
| Streamlit Cloud / browser | Not available in this environment | None | Pending deployment |
| PostgreSQL/S3 migration and multi-tenant validation | No automatic cloud DB migration in this release | None | Pending separate cloud acceptance |
