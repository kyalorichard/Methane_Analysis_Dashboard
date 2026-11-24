# Identity and access control

Do not implement password storage or custom authentication in the Streamlit app.
Use the organisation's approved OIDC identity provider (for example, Microsoft Entra ID)
through a trusted identity-aware reverse proxy such as oauth2-proxy or an equivalent
managed gateway.

Required controls before deployment:
- Validate OIDC issuer, audience, signature, expiry and allowed domains.
- Strip client-supplied identity headers at the edge; proxy must set them itself.
- Map immutable OIDC `sub` to `users.oidc_subject`; do not use email as the identity key.
- Resolve tenant membership and role server-side on every request.
- Enforce least-privilege role permissions and tenant-scoped database transactions.
- Require MFA according to ICARDA/CGIAR policy.
- Terminate TLS at the trusted ingress; do not expose internal services publicly.
- Rotate secrets; use a secrets manager in production.
- Add rate limits, session expiry, CSRF protection where applicable, and security logging.

The included compose file is a local integration environment, not a hardened internet-facing
deployment. The API currently demonstrates a service-token boundary only; OIDC middleware,
membership resolution, and tenant-scoped SQL transactions remain implementation tasks.
