# Methane Phenotype Analytics — Updated Professional Release

**Build:** `2026.11.26-professional-refactor`

## What changed

- Workflow-led primary navigation with overlapping/older workbenches moved into an Advanced / Compatibility section.
- A professional study overview with animal-level structure, repeated-animal counts, non-finite values, duplicate rows and recommended next steps.
- Canonical reliability engine in `analysis_engine/reliability.py` for subject–occasion panel construction, balanced-panel ICC, unbalanced long-format ICC(1,1), Bland–Altman agreement and within/between-subject variance.
- Existing `advanced.py` and `release6.py` function names retained as compatibility adapters so older pages and integrations continue to work.
- Page 07 is now for within-animal trajectories; formal ICC estimation is centralised in Page 33.
- Page 08 uses the shared group-comparison service and defaults to animal-level aggregation when an animal ID is available.
- New project uploads retain original source bytes separately from canonical Parquet, with independent SHA-256 checksums and an authorized original-file download.
- Functional ownership audit and additional regression tests.

## Install and run (Windows PowerShell)

```powershell
cd Methane_Analysis_Dashboard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:AUTH_MODE = "development"
streamlit run app.py
```

For local testing only, `AUTH_MODE=development` is acceptable. Do not expose development authentication on a public or institutional network. Configure the approved identity provider/reverse proxy before deployment.

## Existing cloud deployment

Before deploying the updated code to PostgreSQL/S3, back up the database and apply:

```bash
psql "$DATABASE_URL" -f database/migrations/004_original_source_storage.sql
```

The migration adds `datasets.source_storage_key`. New uploads write the canonical Parquet object and the original source object separately using the existing KMS encryption setting. Confirm IAM/KMS permissions allow both writes and authorized source retrieval. Configure S3 lifecycle/retention, versioning and audit logging according to institutional policy.

For local storage, the SQLite schema adds `source_storage_path` and `source_sha256` automatically when the local workspace opens. Back up the local metadata database and `data/local_workspace/` together.

## Test and audit commands

```bash
python -m compileall -q .
pytest -q
python tools/audit_functional_overlaps.py
```

The review environment did not have `pyarrow` or Streamlit installed. The Parquet tests therefore could not execute there, and a live browser smoke test could not be run. Both are declared in `requirements.txt`; install dependencies before local launch. In this environment, 135 tests passed when the Parquet-specific test file was excluded; the full suite had two failures solely because `pyarrow` was absent. Mixed-effects convergence warnings remain visible and must be reviewed rather than suppressed.

## Important limitations

This release is a materially improved research dashboard and codebase, not a fully certified institutional production platform. The original study notebook/protocol is still required for scientific equivalence verification. The Celery worker and FastAPI analysis-run workflow remain scaffolds and need completion and integration testing. Apply database migration and verify cloud IAM/KMS/S3 behavior before production deployment.
