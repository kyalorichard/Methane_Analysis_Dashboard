# Implementation status — v3

| Capability | Status | Notes |
|---|---|---|
| Original 15-module research dashboard | Retained | Existing analytical modules preserved |
| Species & Protocol Configuration | Added | Species adapters, role mapping and protocol review |
| Entra ID integration boundary | Scaffolded | oauth2-proxy OIDC config and trusted-header mode; not yet deployed |
| Multi-user identity context | Partially implemented | Immutable Entra object ID maps to server-side PostgreSQL tenant membership; user provisioning required |
| Tenant/project schema | Implemented as schema starter | Tenant and project memberships, RLS policies; app DB role and cross-tenant tests remain |
| Project workspace | Implemented code path | Tenant-scoped project creation/listing and project membership checks |
| Dataset persistence | Implemented code path | Raw file to private S3 prefix plus checksum, schema, QC and protocol metadata in PostgreSQL; AWS credentials/policies not integration-tested |
| Species framework | Implemented as adapter registry | Sheep/goat/cattle/buffalo/camel/other; study-specific phenotype definitions require validation |
| Background analysis jobs | Scaffolded | Celery task entry point exists; module execution and persisted results remain |
| AWS infrastructure | Starter only | Terraform provisions foundational resources; task registration, IAM, DNS, WAF and full release wiring remain |
| Security/operations | Guidance provided | Requires institutional security review, backup restore, monitoring and penetration testing |

## Release gate
Do not deploy to production until Entra proxy configuration is tested, identity headers are trusted only behind the private proxy path, tenant and project authorization is enforced on every endpoint, database RLS is tested using a non-owner application role, S3 access is restricted by task role and tenant prefixes, and the AWS plan passes institutional security review.


## Streamlit-first increment v4

Added a dedicated Scientific Analysis Workbench page with runnable exploratory workflows for one-way ICC(1,1)/ICC(1,k), animal-level bootstrap intervals, Bland–Altman paired agreement, Welch/Kruskal group comparisons with BH-adjusted pairwise tests, log-log allometry, quantile regression, recording-duration threshold sensitivity, independent-group TOST, and bootstrap cluster stability. The page also exports a JSON analysis manifest and active dataset Parquet. These are not a substitute for prespecified study protocols, mixed-effects variance component models, nested grouped validation, or independent external validation.
