# Phase 2 — Analytical reproducibility

Release date: 26 November 2026

## Scope

Phase 2 builds on Phase 1 project-scoped run history and adds durable, reopenable analysis outputs for the Integrated Analysis Centre.

### 1. Reproducibility artifact format

Each new Integrated Analysis Centre run attempts to save a project-linked ZIP artifact containing:

- Run manifest and summary JSON.
- Every pandas result table as CSV.
- The exact DataFrame supplied to the analysis, stored as Snappy Parquet when the Parquet engine is available and CSV as a fallback.
- The saved phenotype-distribution Plotly figure as HTML.
- Dataset fingerprint, project/dataset identifiers, measurement protocol, variable roles, validation design, random seed, Python and package versions, and application version/commit when configured.

The artifact format is versioned (`methane-analysis-run-artifact`, version 1). The loader rejects unsupported versions, duplicate archive paths, path traversal and missing required metadata. No pickle files or executable model objects are loaded.

### 2. Local and cloud persistence

- Local mode stores artifacts under `METHANE_RUN_ARTIFACT_DIR` (default `data/analysis_artifacts`) and records the artifact path in the SQLite analysis-run registry. Access is checked against the local project owner and run scope.
- Cloud mode stores artifacts in the configured S3 bucket under the tenant/project/run prefix, with SSE-KMS encryption and SHA-256 object metadata. The existing PostgreSQL `analysis_runs.result_key` field points to the artifact. Project access and tenant transaction checks are performed before attaching or loading the artifact; an audit event is written on save.
- Existing local SQLite registries add `artifact_key` automatically. No new PostgreSQL migration is required for artifact pointers because `analysis_runs.result_key` already exists in the platform schema.
- The cloud runtime role needs the existing tenant-prefix S3 `PutObject`, `GetObject` and `DeleteObject` permissions.

### 3. Reopen and rerun workflow

The Analysis Run History page now:

- Shows whether each run has a full artifact or metadata only.
- Reopens saved result tables, manifest, scientific caveats and distribution figure.
- Allows download of the saved artifact.
- Restores the exact archived input into the current Streamlit session without modifying the stored project dataset.
- Restores the saved analysis selections and navigates to the Integrated Analysis Centre to configure a new run from the prior design.

The Analysis Run Comparison page can compare common persisted result tables side by side and show cell-wise numeric differences where the saved table shapes and column layouts match. These are descriptive differences, not statistical tests.

### 4. Project portability

Project archives now optionally include analysis-run manifests and full artifacts. Import creates new run IDs under the destination project, preserves the source run ID as provenance, remaps dataset IDs where the corresponding project dataset was included, and reattaches artifacts to the new project. Older archives without the `analysis_runs` field remain supported.

The archive format version remains 1 because `analysis_runs` is an optional backward-compatible manifest field. Project archives retain the existing 200 MB maximum size.

### 5. Deliberate boundaries

- Fitted model binaries, model pickles, raw execution logs and live process state are not persisted.
- The artifact captures the data actually passed into the Integrated Analysis Centre, not the original upload bytes. The original upload remains in the project dataset's source-preservation workflow when it was saved there.
- The artifact is a reproducibility record and result snapshot. Re-running the analysis may produce small numerical differences across hardware, package versions, or solver implementations; provenance records the available software versions and random seed to support interpretation.
- Full artifacts are saved only when a project is active. A run without an active project may retain metadata in local mode, but it is not presented as a fully reopenable project artifact.
- Cloud S3/PostgreSQL integration has not been exercised against a live deployment in this build environment; deployment IAM, KMS, database RLS and bucket configuration must be validated in the target environment.

## Validation

The Phase 2 tests cover artifact serialization and reopening, exact input snapshot restoration, local artifact persistence and user/project access isolation, and project archive export/import of analysis artifacts. The full project test suite should be run before deployment.
