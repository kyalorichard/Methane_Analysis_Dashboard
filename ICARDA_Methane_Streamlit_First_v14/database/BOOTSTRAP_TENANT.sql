-- Run once as a controlled database administrator after schema.sql.
-- Replace all values. The Entra object ID is the immutable `oid` claim from the ID token.
INSERT INTO tenants (name, slug) VALUES ('ICARDA Research', 'icarda-research')
ON CONFLICT (slug) DO NOTHING;

-- Replace <ENTRA_OBJECT_ID> and <USER_EMAIL> with approved institutional identity details.
INSERT INTO users (oidc_subject, email, display_name)
VALUES ('<ENTRA_OBJECT_ID>', '<USER_EMAIL>', '<DISPLAY_NAME>')
ON CONFLICT (oidc_subject) DO UPDATE SET email=EXCLUDED.email, display_name=EXCLUDED.display_name;

INSERT INTO tenant_memberships (tenant_id, user_id, role)
SELECT t.id, u.id, 'tenant_admin'
FROM tenants t CROSS JOIN users u
WHERE t.slug='icarda-research' AND u.oidc_subject='<ENTRA_OBJECT_ID>'
ON CONFLICT (tenant_id,user_id) DO UPDATE SET role=EXCLUDED.role;

-- Add additional users with roles researcher, analyst or viewer after approval.
