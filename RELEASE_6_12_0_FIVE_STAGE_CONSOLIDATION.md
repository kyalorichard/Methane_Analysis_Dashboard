# Release 6.12.0 — Five-stage consolidation implementation

## Scope and status
This release implements additional shared architecture, configuration validation, data-context safeguards, unified local metadata-store support, navigation coverage, and scientific time-series corrections. It does not claim live cloud/browser certification.

## Stage 1 — Source architecture
- The storage facade remains the single supported page-facing backend selector.
- Added `platform_core.analysis_context.resolve_analysis_context()` as the shared analysis context resolver.
- The common `get_data()` entry point now resolves and caches project, dataset, species, dataset fingerprint and scoped settings for analytical pages.
- Added explicit navigation links for all 38 page scripts; the two previously orphaned specialist pages are now reachable.

## Stage 2 — Configuration
- Central settings are loaded for every page using the shared `get_data()` entry point.
- Validation now checks forecast prediction interval bounds, configured validation group, and longitudinal date/occasion metadata.
- Existing module-specific settings integrations are retained; explainability now uses configured holdout fraction and seed, and group comparisons display the configured alpha threshold.
- This release does not claim every individual UI parameter is consumed by every engine. The active settings object and validation results are available in `st.session_state['active_analysis_context']`.

## Stage 3 — Data lifecycle
- Existing project-switch invalidation is retained.
- A shared analysis context fingerprints the active dataset and records its project/dataset/species scope.
- The context is rebuilt through the shared `get_data()` entry point, avoiding independent page-level reconstruction of core context.

## Stage 4 — Analytics and scientific safeguards
- Forecast evaluation preserves missing calendar bins instead of dropping them and collapsing non-adjacent time points.
- Training-window imputation is restricted to observed training history; future holdout observations are not used to impute training data.
- Holdout metrics exclude missing actual outcomes while retaining the chronological index.
- Existing grouped classification validation and specialist scientific methods are retained.

## Stage 5 — Persistence and acceptance
- Local workspace, settings/experiment registry, and run registry can share one SQLite metadata file using `METHANE_METADATA_DB`.
- Explicit legacy overrides (`LOCAL_WORKSPACE_DB`, `ANALYSIS_REGISTRY_PATH`, `METHANE_RUN_REGISTRY`) take precedence to prevent accidental relocation.
- Added regression tests for the shared metadata database, analysis context, and missing time-bin preservation.
- No automatic migration of existing SQLite databases is performed. Back up and migrate data before changing database paths.
- Run the full test suite in an environment with all `requirements.txt` dependencies installed, including `pyarrow`.
- Live Streamlit Cloud, PostgreSQL/S3, authentication, multi-user isolation, browser and restart-persistence tests remain deployment acceptance tasks.

## Unified local metadata configuration
Set `METHANE_METADATA_DB=/persistent/path/methane_metadata.sqlite3`. Do not set the legacy override variables to different paths if a single SQLite metadata file is intended. Keep `LOCAL_PROJECT_STORAGE_DIR` on persistent storage; dataset Parquet files remain there.

## Migration warning
Setting `METHANE_METADATA_DB` changes where new metadata is written. Existing databases are not automatically merged. Back up `data/local_workspace/workspace.sqlite3`, `data/analysis_registry.sqlite3`, and `platform_data/analysis_runs.sqlite3` (or configured equivalents), then perform a tested SQLite table-level migration before switching production.
