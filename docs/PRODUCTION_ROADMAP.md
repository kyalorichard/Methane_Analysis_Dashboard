# Production roadmap — Methane Phenotype Analytics

## Target architecture
- Streamlit: researcher-facing dashboard and project workspace.
- FastAPI: authenticated service boundary and project/dataset/analysis APIs.
- PostgreSQL: tenants, memberships, projects, dataset metadata, analysis runs and audit events.
- S3-compatible object storage: immutable raw uploads, harmonised Parquet datasets and outputs.
- Redis + Celery: asynchronous model fitting, resampling, bootstrapping and report generation.
- OIDC identity provider + trusted reverse proxy: institutional authentication and role claims.
- Central logs/metrics, backups, restore tests and deployment monitoring.

## Phased implementation
1. **Identity and tenancy:** OIDC, membership administration, roles, PostgreSQL row-level security tests.
2. **Data lifecycle:** upload quarantine, checksum, schema profile, immutable raw object, validated Parquet derivative, data dictionary and versioning.
3. **Analysis orchestration:** job registry, queue, progress/status, cancellation, retries and resource limits.
4. **Scientific governance:** species-specific adapters, protocol metadata, versioned phenotype definitions, reproducible parameters, grouped validation and analysis manifests.
5. **Operations:** TLS ingress, secret manager, automated backups, restore drills, structured logs, alerting, CI/CD and vulnerability scanning.
6. **Validation and release:** unit/integration/security tests, user acceptance testing, documented SOPs and controlled production release.

## Species architecture
Keep a common observation/project envelope, but do not force identical phenotype semantics across species.
Each species adapter must declare:
- required identifiers and repeated-measure keys;
- measurement instrument and protocol;
- units, calibration and valid ranges;
- phenotype definitions and minimum recording duration;
- species-specific QC rules;
- supported analysis modules and validation design.

## Data governance
- Tenant isolation must apply to database queries and object-storage keys/policies.
- Preserve immutable raw files; derived datasets are versioned.
- Record uploader, timestamp, checksum, source filename, schema mapping and QC report.
- Never label concentration/AUC as methane mass flux without a validated calibration.
- Use animal-grouped validation where records repeat within animals.
- Keep synthetic demo data clearly labelled and segregated from empirical project data.
