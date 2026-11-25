# Release 6.12.1 — Settings consumption, service consolidation and metadata migration

## Scope
This release addresses three outstanding areas from the 6.12.0 acceptance matrix:

1. Make shared analysis settings available through one validated active context and consume model/preprocessing settings in the grouped regression benchmark.
2. Establish a canonical service registry for shared scientific operations. Specialist estimators with different statistical assumptions remain separate and are exposed explicitly rather than silently substituted.
3. Automatically migrate legacy local SQLite metadata into one canonical SQLite metadata database, preserving source databases and creating timestamped backups.

## Settings consumption implemented
- `platform_core.analysis_context.resolve_analysis_context()` loads project/species-scoped settings and fingerprints the active dataset.
- `analysis_engine.ui.get_data()` resolves that context for pages using the shared data entry point.
- `analysis_engine.ml.grouped_regression_benchmark()` now consumes configured numeric/categorical imputation, numeric scaling, per-model hyperparameters and the configured random seed.
- The existing page integrations for statistical alpha, group comparisons, clustering, repeatability, explainability and forecasting remain in place.
- `active_settings_section()` provides a defensive-copy accessor for future modules.

This is not a claim that every individual setting in the Settings form is consumed by every page. Settings that have no scientifically valid equivalent in a particular analysis are not forced into that analysis. See the acceptance matrix for the explicit distinction.

## Service consolidation
`analysis_engine.service_registry` is the canonical discovery/dispatch point for common grouped modelling, repeatability, phenotype validation/evidence and report-bundle services. Different repeatability estimators are retained where their designs/estimands differ (long-format one-way random effects versus balanced-panel ICC1/ICC2/ICC3). These are not interchangeable calculations.

The UI pages are retained to avoid removing specialist workflows. Full visual page merger is not performed where it would remove methods or change estimands. Future pages should call shared services rather than copy their calculations.

## Automatic local metadata migration
The canonical local metadata path is:

`METHANE_METADATA_DB` if set, otherwise `data/methane_metadata.sqlite3`.

On first connection, the migration service checks these legacy sources when they exist:
- `LOCAL_WORKSPACE_DB`, otherwise `data/local_workspace/workspace.sqlite3`
- `ANALYSIS_REGISTRY_PATH`, otherwise `data/analysis_registry.sqlite3`
- `METHANE_RUN_REGISTRY`, otherwise `platform_data/analysis_runs.sqlite3`

Migration is idempotent per source path. It creates a timestamped `.pre_migration_YYYYMMDDTHHMMSSZ.bak` SQLite backup, copies recognised metadata tables in dependency order, inserts source-only rows without overwriting destination records, records migration status, and leaves all legacy databases intact. Column intersection permits compatible legacy schema variations. Any migration errors are returned in the report and must be reviewed before production promotion.

Legacy explicit environment variables are still accepted as source locations. For a new unified local deployment, set `METHANE_METADATA_DB` and remove old per-registry path overrides after migration has been verified. Keep Parquet/object storage on persistent storage separately.

## Tests
- Added tests for idempotent metadata migration, source backups, and data preservation.
- Added tests proving configured Random Forest hyperparameters and random seed are used by the grouped regression estimator.
- Python compilation passed.
- Test suite excluding `tests/test_dataset_formats.py`: 112 passed, 9 warnings.
- The two Parquet tests were not run in this environment because `pyarrow` is unavailable here. `pyarrow` remains declared in `requirements.txt`; run the full suite in an environment with dependencies installed.

## Not certified
No live Streamlit Cloud browser test, PostgreSQL/S3 migration, multi-user isolation test, or production dataset scientific validation was performed. Cloud PostgreSQL metadata stores are not automatically merged into local SQLite; use a separately reviewed cloud migration plan for that topology.
