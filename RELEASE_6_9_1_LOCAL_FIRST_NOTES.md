# Release 6.9.1 — Local-first persistent project workspace

## Changes
- Added SQLite-backed local project metadata, dataset registry and version checkpoints.
- Added filesystem storage of immutable Parquet dataset files with SHA-256 verification.
- Project Workspace automatically selects local mode if PostgreSQL and S3 are not both configured.
- Added explicit `PROJECT_STORAGE_BACKEND=local|cloud` override.
- Added configurable `LOCAL_PROJECT_STORAGE_DIR`.
- Existing project archive import/export and duplication workflows use the same workspace interface.

## Storage layout
`data/local_workspace/workspace.sqlite3` stores metadata. Project datasets and checkpoint manifests are stored under `data/local_workspace/projects/<tenant>/<project>/`.

## Limitations
- Local mode is single-instance and intended for local/standalone deployments.
- It uses the existing development/local identity mode unless deployed authentication is separately configured. It does not provide cross-user shared tenant provisioning.
- Project ZIP import/export still requires the project's supported Parquet dependencies and preserves the existing archive format.
- Version checkpoints are metadata/dataset-manifest snapshots, not binary rollback snapshots.
- The local workspace must be on persistent disk; ephemeral containers will lose data on replacement.

## Validation
Run `python -m compileall -q app.py pages platform_core analysis_engine` and `pytest -q tests/test_project_archive.py tests/test_platform_security_contract.py`.
