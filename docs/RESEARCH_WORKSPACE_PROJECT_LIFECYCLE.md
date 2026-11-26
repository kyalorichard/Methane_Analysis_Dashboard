# Research Workspace: project lifecycle

The Research Workspace supports four distinct entry points:

1. **Open existing project** — select a saved tenant-scoped project and optionally restore one of its stored datasets into the active analysis session.
2. **Create new project** — create a persistent project record and make it the active project.
3. **Import project archive** — validate a portable ZIP archive and create a new project from its metadata, datasets, protocols and supported analysis-state metadata.
4. **Save project checkpoint / export** — create a metadata and dataset-manifest checkpoint, or download a portable ZIP backup.

## What is restored when opening a project

When a dataset is selected, the workspace reloads its canonical Parquet data and restores the saved species, variable mapping and measurement protocol. It also sets the active project and dataset identifiers and the project/species analysis scope. The dataset and configuration are retrieved from the selected storage backend, not from Streamlit session memory.

Opening a project without selecting a dataset clears any previously loaded dataset from the current session to avoid accidentally analysing data from another project.

## Persistence boundaries

Project metadata and stored datasets persist in the configured local SQLite/filesystem or cloud PostgreSQL/S3 backend. Dataset-level species, variable mappings and measurement protocol metadata are persisted with the dataset configuration. Project-scoped analysis settings are persisted by the Analysis & Model Settings workflow.

A project checkpoint records project metadata and a dataset manifest; it is not a point-in-time backup of the database. A portable project ZIP includes project metadata, canonical Parquet datasets, protocol metadata and supported analysis-state metadata. It does not promise to reconstruct fitted model binaries or every historical result artifact.

The recently opened list is currently scoped to the active Streamlit browser session. Projects remain available after sign-out or application restart through **Open existing project**, even when the recent-session list is reset.
