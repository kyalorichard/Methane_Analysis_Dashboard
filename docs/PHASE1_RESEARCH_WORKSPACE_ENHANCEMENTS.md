# Phase 1 — Research workspace integration

> Historical release notes. Phase 2 supersedes the Phase 1 limitation on reopenable result artifacts; see `PHASE2_ANALYTICAL_REPRODUCIBILITY.md`.

Release date: 26 November 2026

## Scope

This update strengthens the project/data lifecycle without replacing existing analytical modules.

### 1. Tenant- and project-scoped analysis history

- Analysis-run records now carry tenant, project, user, dataset and module scope in the local SQLite registry.
- Run-history and comparison pages request records for the authenticated tenant and user, and the active project when one is selected.
- The cloud backend writes run metadata to the existing PostgreSQL `analysis_runs` table under the tenant transaction context and project access checks.
- Analysis & Model Settings now uses tenant/project/user-scoped PostgreSQL storage in cloud mode, including immutable configuration snapshots. Local mode continues to use SQLite.
- Cloud run records retain the manifest and summary in the JSONB `parameters` field and record an audit event.
- The registry continues to store metadata and summaries only. It does not claim to persist fitted model binaries or complete result tables.
- Legacy unscoped local rows are retained, not silently assigned to a user or project. They are not returned by scoped queries until explicitly migrated or re-run under a project context.

### 2. Durable prepared-dataset versions

The Data Preparation Studio now offers **Save prepared dataset version**. It:

- Saves the current prepared DataFrame as a new canonical Parquet dataset in the active project.
- Preserves the previous saved dataset rather than overwriting it.
- Attaches the source dataset ID/name, transformation log, before/after row counts, column names and preparation timestamp to dataset metadata.
- Persists the species, variable-role mapping and measurement protocol.
- Makes the new dataset version active after successful persistence.

The upload payload for a prepared version is the Parquet representation of the prepared DataFrame. The original source dataset remains separately preserved in its own dataset record.

### 3. Consistent active workspace context

Analytical page headers now display the active project, dataset and whether the dataset is persisted or only available in the current Streamlit session.

Switching projects clears the active dataset and associated analysis state to prevent accidental analysis of a dataset from a different project. Creating or importing a project also clears any previous active dataset.

## Deployment notes

- Local mode stores run metadata in the same configured SQLite metadata database used by the local workspace. The local workspace is intended for a single persistent application instance.
- Cloud mode uses the existing PostgreSQL `analysis_runs` table and tenant row-level security. Apply `database/migrations/007_project_settings.sql` (or the updated `database/schema.sql`) to add tenant-scoped project settings and history. Ensure the database application role is configured according to the production deployment guide.
- Cloud analysis history requires an active tenant, a project the user can write to, and an authenticated user identity. A saved project dataset is linked when `active_dataset_id` is available; temporary datasets can still be associated with a project run without a dataset foreign key.
- This update does not yet persist all analysis result tables, figures or fitted model objects as independently reopenable artifacts. The Integrated Analysis Centre ZIP remains the complete portable analysis package for its current outputs.
- Cloud project archive export/import currently includes project settings; experiment-registry records remain in the local SQLite registry and are not exported from cloud PostgreSQL by this phase.
- This update does not make local filesystem storage durable on ephemeral hosting. Use PostgreSQL + S3 for deployed Streamlit Cloud or multi-instance hosting.

## Validation

The phase 1 regression suite covers tenant/project/user run isolation, legacy local API compatibility, history/comparison scoping, prepared dataset persistence wiring and shared workspace context. Python compilation and the test suite should be run in the target deployment environment before release.
