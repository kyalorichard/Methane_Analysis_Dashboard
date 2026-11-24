# v15 Dataset Format Update — CSV / Parquet Uploads

## Summary
- Added CSV (`.csv`) and Apache Parquet (`.parquet`, `.pq`) ingestion.
- Retained Excel (`.xlsx`, `.xls`) upload support for backward compatibility.
- Standardised new persistent project dataset objects to Snappy-compressed Parquet.
- Scientific modules continue to consume pandas DataFrames; no analysis-module interface changes are required.
- Dataset registry now records source format, canonical storage format, canonical SHA-256 and source-file SHA-256.
- Added Parquet loading for newly stored datasets while retaining CSV/Excel loading for legacy objects.

## Files changed
- `analysis_engine/io.py`
- `app.py`
- `pages/00_Project_Workspace.py`
- `platform_core/workspace.py`
- `database/schema.sql`
- `tests/test_dataset_formats.py`
- `README.md`

## Database migration
Re-apply `database/schema.sql` to add `source_format` and `source_sha256` to an existing `datasets` table. The schema uses additive `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements.

## Dependency
`pyarrow>=15` is already declared in `requirements.txt`. Install project dependencies before testing Parquet read/write locally:

```bash
python -m pip install -r requirements.txt
```

## Validation
Python compilation passed. CSV/unsupported-extension tests and architecture/security contract tests passed in the build environment. Parquet round-trip tests could not execute in the build environment because `pyarrow` was not installed there; they are included and should pass after installing the declared requirements.

## Storage behavior
New uploads saved through Projects & datasets are converted to canonical Parquet and stored as `data.parquet` in the configured S3-compatible bucket. The original upload is not retained as a second object; its filename, source extension and SHA-256 are recorded in the dataset registry/audit metadata.
