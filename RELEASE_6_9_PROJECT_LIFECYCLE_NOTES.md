# Release 6.9.0 — Project Lifecycle, Portable Import/Export and Version Checkpoints

## Purpose

Release 6.9.0 extends the Release 6.8.2 research workspace into a project-centred workflow. Researchers can create projects, upload and persist datasets, reopen stored datasets, duplicate projects, export portable project archives, import an archive as a new project, and create project metadata/dataset-manifest checkpoints.

## Project workspace

The Project Workspace now provides three operational areas:

1. **Project overview** — project identity, species, description, dataset summary, dataset reload into the analysis session, and independent project duplication.
2. **Datasets & protocols** — CSV, Parquet/PQ and Excel ingestion; measurement instrument, method, units, calibration status, SOP and minimum recording duration; QC summary; canonical Snappy Parquet persistence in S3; SHA-256 integrity metadata.
3. **Versioning & portability** — metadata/dataset-manifest checkpoints and portable project ZIP export.

The workspace also exposes separate create and import tabs, including when the tenant has no existing projects.

## Portable archive format v1

A ZIP archive contains:

- `manifest.json`: format/version, export timestamp, project metadata, dataset metadata, protocol metadata and SHA-256 checksums.
- `datasets/NNNN.parquet`: canonical Parquet representation of every stored dataset.
- `research_state`: optional analysis settings and experiment metadata available under the authenticated user's project-name scope.

The archive deliberately does not contain tenant IDs, database primary keys, S3 object keys, credentials, access tokens or other infrastructure-specific identifiers. Import creates a **new project** in the active tenant and persists datasets as new S3 objects and database records.

### Import safeguards

- ZIP format and archive schema version are validated.
- Duplicate member names, absolute paths, path traversal and backslash paths are rejected.
- Archive and member size limits are 200 MB, aligned with Streamlit's configured upload limit.
- Dataset members must be under `datasets/` and use `.parquet`.
- SHA-256 checksums and row/column dimensions are checked.
- Dataset species must match the project's primary species.
- Import is a new-project operation; it does not overwrite an existing project.

If an import fails after the project record is created, the partial project is retained for audit/recovery. The UI reports the project ID and asks the administrator to inspect it before retrying; it does not silently delete potentially useful imported data.

## Project duplication

Duplication creates a new project and copies all datasets and measurement protocol metadata into independent storage objects. It does not modify the source project. A failed replication may leave a clearly reported partial copy for administrative review.

## Version checkpoints

The `project_versions` table stores immutable metadata and dataset-manifest snapshots with sequential per-project version numbers and audit events. Dataset objects remain in S3. These checkpoints are **not full data backups and do not implement point-in-time rollback**. For recoverable project backup/transfer, use the portable project ZIP export.

## Analysis state

The archive can include settings and experiment records from the existing SQLite experiment registry, scoped by authenticated subject and project name. On import, these records are restored under the importing user's identity and destination project name. This is metadata restoration only; fitted estimator binaries, raw worker execution logs, and historical result artifacts are not included unless separately persisted as datasets.

The analysis settings page currently uses a local SQLite registry. In a multi-replica production deployment, set `ANALYSIS_REGISTRY_PATH` to a shared durable volume or migrate the registry to the tenant database before relying on cross-instance consistency. The archive import/export feature does not make that local registry globally shared.

## Infrastructure requirements

- `DATABASE_URL` configured. For an existing database, apply `database/migrations/0069_project_versions.sql`; for a fresh database, `database/schema.sql` includes the new `project_versions` table and RLS policy.
- `S3_BUCKET` configured with least-privilege read/write/delete permissions for project dataset objects.
- `AWS_REGION` configured where required.
- `pyarrow` installed (required for Parquet serialization/deserialization).
- Authenticated tenant/user provisioning and project role grants configured.

## Verification performed

- Python compilation and AST compilation for the application, pages, analysis engine and platform modules.
- Focused project archive, architecture and security-contract tests: 9 passed.
- Full test suite: 91 passed, 2 failed because the build environment does not have `pyarrow` installed. Both failures are existing Parquet-format tests that require this declared runtime dependency. The project archive unit tests validate archive structure, SHA-256 tamper detection and path traversal rejection.
- Browser-based Streamlit interaction, live PostgreSQL RLS behavior, S3 integration, and end-to-end import/export against a deployed tenant were not exercised in this build environment.
