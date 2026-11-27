# Phase 12 — Versioned Model Registry

## Purpose
Add a user-scoped model registry to the Unified Research Model Lab for registering fitted regression and classification pipelines, tracking immutable versions, recording provenance, applying an explicit approval/retirement lifecycle, and reusing approved models on another active project dataset.

## Implemented
- `analysis_engine/model_registry.py` provides model metadata, immutable version records, artifact integrity hashes, status transitions, artifact download/read, and model loading.
- Model metadata records model family, task, outcome, ordered predictors, grouping column, species scope, source project, dataset fingerprint, training records/groups, random seed, validation metadata, notes, status, timestamps and SHA-256.
- Model artifacts use `skops.io`; pickle/joblib are deliberately not used.
- Non-default artifact types are surfaced for explicit user review before loading.
- The Model Lab supports registering a new model or creating a subsequent version of an existing lineage. A new version must retain the same task, estimator, outcome and ordered predictor list.
- Only approved model versions can be loaded for prediction from the registry. Approval requires explicit acknowledgement that validation evidence and intended-use limits have been reviewed.
- Models can be listed across projects belonging to the same authenticated tenant/user scope. This supports reuse across projects when the destination dataset contains the registered predictors.
- Predictions can be inspected and exported as CSV.

## Storage and deployment boundary
This release stores metadata in the configured local SQLite registry (`ANALYSIS_REGISTRY_PATH` / `METHANE_METADATA_DB`) and `.skops` artifacts under `MODEL_REGISTRY_DIR` (default `data/model_registry`). The authenticated tenant and subject are combined in the user scope to prevent cross-tenant user collisions.

**PostgreSQL/S3 model artifact persistence is not implemented in this phase.** On Streamlit Cloud or any ephemeral filesystem, local SQLite and artifact files may be lost on restart/redeployment. Configure a persistent mounted volume before relying on registry durability. Do not claim durable cloud governance until a PostgreSQL metadata backend and S3 artifact backend are added and tested.

## Scientific governance
- Registration fits the selected estimator on the full active development cohort. This is a deployment fit, not a validation estimate.
- Validation metrics are not automatically fabricated or inferred from training performance. The metadata field is available, but this page currently registers an empty validation-metrics object; use the dedicated grouped comparison and external-validation workflows to assess performance.
- Approval is a human governance action, not an automated scientific endorsement.
- Reuse checks required predictor availability but does not automatically harmonise units, instruments, outcome definitions, or sampling protocols. Confirm these before applying a registered model to another cohort.
- The dataset fingerprint records the development data used at registration/versioning time.

## Security
- `skops.io` is required (`skops>=0.10`). Install dependencies before deployment.
- Artifacts are SHA-256 checked before inspection or loading.
- The loader rejects unreviewed non-default Python types. Users must explicitly confirm trust for any types reported by skops.
- Model metadata queries are restricted by user scope. The current local registry is not a substitute for a shared, audited multi-user cloud registry.

## Validation
- Unit tests cover registration, listing, user isolation, artifact integrity, immutable version retrieval, lifecycle updates and invalid input handling.
- Full Python compilation and project tests are run for this release, excluding dataset-format tests that require PyArrow when unavailable in the audit environment.
- Live Streamlit interaction, skops artifact round-trip in the deployment environment, PostgreSQL/S3 persistence and cloud deployment are not certified by the local test suite.
