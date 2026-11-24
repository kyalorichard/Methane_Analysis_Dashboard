# Release 6.8 — Persistent Settings, Nested Tuning and Experiment Registry

## Scope-aware settings
- Settings are stored in SQLite and keyed by user scope, project/study scope and species scope.
- `ANALYSIS_REGISTRY_PATH` controls the registry location; default: `data/analysis_registry.sqlite3`.
- Existing Release 6.7 JSON settings are migrated in memory with defaults for new fields and can be re-imported.
- The default user scope is `local-user` unless the application session exposes `user_id`, `username` or `email`. Production deployments must connect this to the authenticated principal and enforce tenant authorization.
- SQLite persistence survives process restarts only when the configured path is on durable storage. The production Compose dashboard mounts the named `analysis_registry_data` volume at `/app/data`. For horizontally scaled deployments, use a shared durable database or adapt the registry to the tenant database; do not put a local SQLite file on ephemeral container storage.

## Nested grouped hyperparameter optimisation
- Optional random search is performed independently inside each outer training fold.
- Inner CV uses `GroupKFold` and the same independent grouping unit; preprocessing remains inside the estimator pipeline.
- The outer test fold is not used for hyperparameter selection.
- Search spaces are defined for Random Forest, Extra Trees, HistGradientBoosting, SVR and KNN.
- Supports random search, exhaustive grid search and optional Bayesian TPE optimisation via Optuna. `tuning_iter` controls sampled candidates for random/Bayesian search; grid search evaluates the full defined grid. This can be computationally expensive; start with 5–10 candidates for exploratory runs.

## Conventional-model controls
- GEE working correlation: exchangeable, independence or autoregressive.
- Mixed-effects estimation: ML or REML.
- Quantile regression quantile and spline basis knot count.
- These controls affect the matched benchmark where applicable. They do not silently alter every other analysis page.

## Experiment registry
- Saves experiment name, scope, configuration, selected models, target, predictors, grouping unit, metrics, paired comparisons and analysis metadata.
- Access is filtered by user scope; a user cannot retrieve another user’s experiment through the registry API.
- OOF row-level predictions are not persisted in this registry by default. Download them separately from the comparison page.

## Validation
- Unit tests cover settings persistence and scope isolation, experiment round-trip and user isolation, nested group-aware random search and grid search, and model-comparison parameter handling.
- Full suite: 87 passed, 2 failed; both failures are the existing Parquet tests because `pyarrow` is not installed in the build environment.
- Browser-based Streamlit end-to-end testing is not performed in the build environment; Streamlit is not installed in the build environment.
- The exposed GEE working-correlation choices are exchangeable and independence. Autoregressive structures are intentionally not exposed because this comparison page does not yet collect an explicit within-cluster time index; using AR without a defensible time ordering would be misleading.
