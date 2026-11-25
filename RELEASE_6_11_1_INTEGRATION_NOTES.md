# Release 6.11.1 — Analytical Integration and Acceptance Improvements

## Scope
This release continues the Release 6.11 consolidation work. It improves shared configuration scoping, removes remaining direct storage-backend selection from the species/protocol page, prevents stale in-memory data from crossing project boundaries, and connects saved settings to additional analytical workflows.

## Changes

### 1. Consistent storage access
- The landing page no longer imports the cloud workspace implementation directly.
- The Species & Protocol Configuration page now resolves the configured backend through `platform_core.storage`.
- Local/cloud selection and configuration validation are centralised in the storage facade.

### 2. Project and dataset isolation
- The shared project selector now includes a short project ID to disambiguate projects with identical names and species.
- Switching between projects clears active in-memory data and analysis results so results from one project cannot silently appear under another project.
- The active project ID and species are written to the settings scope.

### 3. Authenticated settings scoping
- Settings scope now resolves the authenticated subject from the principal established by shared navigation.
- Project and species scopes are resolved from the active project/session context.
- This reduces the risk of different authenticated users sharing the fallback `local-user` settings scope when navigation has already established a principal.
- The Settings page species list now uses the canonical `goat` key rather than `goats`.

### 4. Central settings consumed by analytical pages
- Statistical Models: significance threshold is loaded from central settings and applied to the coefficient interpretation table.
- ML Benchmarking: grouping column and cross-validation fold defaults are loaded from central settings.
- Clustering & PCA: configured minimum cluster count informs the default cluster selection.
- Repeatability & Reliability: configured animal and occasion columns inform the selected data structure.
- Advanced ML Validation & Explainability: grouping variable, random seed and grouped-fold defaults are loaded from central settings.
- Time-Series Forecasting continues to load forecast defaults from central settings.

### 5. Settings validation
Additional validation covers forecast holdout fraction, SVR lag count, tuning iteration count, repeatability minimum observations and reporting decimal places.

### 6. Registry database configuration
The settings/experiment registry and run registry now recognise `METHANE_METADATA_DB` as a shared metadata database path. Existing legacy environment variables take precedence to avoid silently relocating existing metadata. To opt in to one SQLite metadata file, configure `METHANE_METADATA_DB` and ensure `ANALYSIS_REGISTRY_PATH` and `METHANE_RUN_REGISTRY` are not set to different locations. This does not migrate existing databases automatically; back up and migrate existing metadata before changing production paths.

## Verification
- `python -m compileall -q app.py analysis_engine platform_core pages tests`: passed.
- Focused integration/storage/settings/forecast tests: 13 passed, 3 statsmodels convergence warnings.
- Broader suite excluding `tests/test_dataset_formats.py`: 106 passed, 9 warnings.
- Full suite: the two Parquet-format tests cannot run in this execution environment because `pyarrow` is not installed. `pyarrow>=15` is already declared in `requirements.txt`. Attempted installation was blocked by unavailable package-index network access.

## Remaining acceptance work
This release does not claim that all settings are consumed by all 38 pages. Some settings remain configuration-only until their corresponding analysis engines support them. The project workspace, settings/experiment registry and run registry remain separate persistence stores by default; the shared metadata path is opt-in and requires an explicit migration plan. Cloud PostgreSQL/S3, Entra authentication, Streamlit browser rendering, and restart persistence have not been tested against a live deployment. Mixed-effects and ARIMA/SARIMA synthetic tests emit convergence warnings; model diagnostics must be reviewed for real study data.

## Deployment
1. Back up the existing persistent workspace directory and SQLite databases.
2. Deploy the complete repository, not isolated files.
3. Confirm `pyarrow` installs from `requirements.txt` in Streamlit Cloud.
4. Confirm `PROJECT_STORAGE_BACKEND` and persistent storage settings match the deployment target.
5. Test sign-in, project switching, dataset switching, settings save/reload, Parquet import, analysis execution, and application restart before promoting to production.
