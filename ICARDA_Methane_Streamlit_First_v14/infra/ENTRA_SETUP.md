# Microsoft Entra ID setup

1. Register a single-tenant web application in the ICARDA/CGIAR Entra tenant (or the tenant approved by IT).
2. Add redirect URI: `https://<APP_DOMAIN>/oauth2/callback`.
3. Create a client secret or, preferably, use a certificate/managed secret rotation process. Store it in AWS Secrets Manager; never commit it.
4. Configure OIDC issuer: `https://login.microsoftonline.com/<TENANT_ID>/v2.0`.
5. Request only `openid profile email` unless an approved directory integration requires additional scopes.
6. Restrict sign-in to approved tenant users/groups and require MFA per institutional policy.
7. Configure oauth2-proxy `oidc_user_id_claim = "oid"` so the trusted user header carries the immutable Entra object ID. Provision that object ID in `users.oidc_subject`. The dashboard resolves tenant membership and role from PostgreSQL; roles are never accepted from editable email/domain claims.
8. Configure oauth2-proxy to forward identity headers only to the Streamlit/API services. The public load balancer must never permit direct access to app container ports.
9. Rotate client/cookie secrets and review sign-in logs and access events.

The Streamlit app trusts `X-Auth-Request-*` identity headers only in `AUTH_MODE=entra_proxy`, then resolves role and tenant membership from PostgreSQL using the immutable Entra object ID. This trust is valid only when network ingress blocks direct access and the proxy overwrites/strips client-supplied identity headers. Provision each user and tenant membership before granting access. The sample config is a template and requires environment substitution and security review.
