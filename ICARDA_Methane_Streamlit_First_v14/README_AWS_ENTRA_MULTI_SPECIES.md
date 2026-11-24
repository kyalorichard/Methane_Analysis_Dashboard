# ICARDA Methane Phenotype Analytics — Entra ID / AWS multi-species foundation

## Included in this release
- Existing 15-module Streamlit research prototype retained.
- Explicit species adapter registry for sheep, goats, cattle, buffalo, camels and other livestock.
- Species-specific variable inference and protocol readiness checks; adapters intentionally do not assume identical phenotype semantics.
- Entra ID trust boundary through oauth2-proxy headers (fail-closed in `AUTH_MODE=entra_proxy`).
- User identity, tenant and role context in the dashboard; local development identity is explicitly marked and is not production authentication.
- PostgreSQL tenant/project/dataset/run/audit schema with RLS policies and project membership table.
- FastAPI identity and project endpoints (database-backed when configured).
- S3/AWS infrastructure starter, ECS task-definition template, Entra setup guide and deployment roadmap.
- New Species & Protocol Configuration module.

## Local development
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:AUTH_MODE="development"
streamlit run app.py
```

Use the supplied sheep dataset from the sidebar. For another species, upload its study dataset and select the species. Review the Species & Protocol Configuration module to map variables and document instrument, method, units, calibration, protocol reference and minimum duration.

## Production identity
Set `AUTH_MODE=entra_proxy` only behind a trusted oauth2-proxy deployment. The proxy must authenticate against Microsoft Entra ID, strip inbound identity headers and set trusted identity headers itself. Network controls must prevent direct access to Streamlit/API container ports. Resolve roles and tenant memberships from PostgreSQL using the immutable Entra object ID; do not accept role/tenant claims directly from end-user-controlled headers. Each user must be provisioned in `users` and `tenant_memberships` before access.

See `infra/ENTRA_SETUP.md` and `infra/oauth2-proxy.cfg`.

## AWS target architecture
Application ingress / ALB → oauth2-proxy (Entra OIDC) → Streamlit and FastAPI → RDS PostgreSQL, S3, Redis/ElastiCache and Celery workers. Use ECS Fargate for container orchestration, Secrets Manager for credentials, CloudWatch for logs/metrics, KMS for encryption, and private subnets for data services.

The Terraform files are an infrastructure starter and are deliberately not represented as production-ready. Complete task-definition registration, IAM, database/API secret provisioning, WAF, alarms, DNS/ACM, backup/restore and security review before deployment.

## Scientific governance
- Keep raw source files immutable and version derived data.
- Store species, measurement instrument, method, units, calibration status, protocol/SOP and duration in dataset metadata.
- Do not equate concentration or AUC with methane mass flux (e.g. g/day) without a validated calibration.
- Keep repeated measurements from the same animal grouped during validation.
- Cross-species comparisons require harmonised constructs and validated measurement comparability; a shared interface does not imply equivalent phenotypes.
- The supplied dataset is sheep data only. Other species adapters are configurable frameworks, not validated biological models.

## Current implementation status
Implemented: dashboard identity context, development auth mode, Entra proxy trust boundary, species adapter metadata and inference, data QC profile, PostgreSQL schema, API project endpoints, infrastructure templates.

Still required for production: full OIDC proxy deployment and configuration, server-side user/tenant membership provisioning, per-project authorization on every API route, tenant-scoped DB transactions with a non-owner app role, dataset version lifecycle and retention, Celery execution and persisted run results, complete task-definition registration and IAM policies, ALB/Route53 wiring, automated security tests, institutional security assessment, user acceptance testing and operational SOPs.
