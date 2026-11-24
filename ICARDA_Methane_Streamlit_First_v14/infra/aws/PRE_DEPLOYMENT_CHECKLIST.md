# AWS + Entra pre-deployment checklist

- [ ] Confirm AWS account, region, data residency and institutional approval.
- [ ] Confirm VPC/subnets, private routing, NAT or VPC endpoints, and security-group boundaries.
- [ ] Register Entra web app; validate tenant, redirect URI, issuer, audience and group restrictions.
- [ ] Store OIDC client secret, cookie secret, DB password and API tokens in Secrets Manager.
- [ ] Configure oauth2-proxy to strip untrusted inbound identity headers and set trusted headers.
- [ ] Ensure ALB reaches only oauth2-proxy; no public route to Streamlit, API, Redis, RDS or MinIO.
- [ ] Create least-privilege ECS execution/task roles; task role limited to approved S3 prefixes and Secrets Manager ARNs.
- [ ] Use RDS app role that does not own tables and does not have BYPASSRLS; test cross-tenant denial.
- [ ] Add project membership checks and tenant authorization to every API operation.
- [ ] Add S3 bucket policy, KMS key policy, versioning, lifecycle and object ownership controls.
- [ ] Add ElastiCache Redis, Celery worker service, task queue limits and retry/dead-letter policy.
- [ ] Add CloudWatch dashboards/alarms, audit retention, RDS backups and restore drills.
- [ ] Add WAF, TLS, DNS, ACM certificate, security headers, rate limits and vulnerability scanning.
- [ ] Complete data-protection impact assessment, retention policy and user acceptance testing.
- [ ] Validate species-specific phenotype definitions, units, calibration and protocol before scientific release.
