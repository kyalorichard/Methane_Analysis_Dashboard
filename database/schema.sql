CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS tenants (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS users (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), oidc_subject TEXT UNIQUE NOT NULL,
 email TEXT NOT NULL, display_name TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS tenant_memberships (
 tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
 user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 role TEXT NOT NULL CHECK(role IN ('tenant_admin','analyst','researcher','viewer')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(tenant_id,user_id)
);
CREATE TABLE IF NOT EXISTS projects (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
 name TEXT NOT NULL, species TEXT NOT NULL CHECK(species IN ('sheep','goat','cattle','buffalo','camel','other')),
 description TEXT, created_by UUID REFERENCES users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,id)
);
CREATE TABLE IF NOT EXISTS project_memberships (
 tenant_id UUID NOT NULL, project_id UUID NOT NULL, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 role TEXT NOT NULL CHECK(role IN ('project_admin','analyst','researcher','viewer')),
 PRIMARY KEY(tenant_id,project_id,user_id),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS datasets (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL, project_id UUID NOT NULL,
 name TEXT NOT NULL, species TEXT NOT NULL, storage_key TEXT NOT NULL, file_format TEXT NOT NULL DEFAULT 'parquet',
 source_format TEXT, sha256 TEXT, source_sha256 TEXT, row_count BIGINT, schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
 qc_summary JSONB NOT NULL DEFAULT '{}'::jsonb, protocol_json JSONB NOT NULL DEFAULT '{}'::jsonb, version INTEGER NOT NULL DEFAULT 1,
 uploaded_by UUID REFERENCES users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id) ON DELETE CASCADE,
 UNIQUE(tenant_id,id), UNIQUE(tenant_id,storage_key)
);
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS source_format TEXT;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS source_sha256 TEXT;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS source_storage_key TEXT;

CREATE TABLE IF NOT EXISTS analysis_runs (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL, project_id UUID NOT NULL,
 dataset_id UUID, module_key TEXT NOT NULL, parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
 status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed','cancelled')),
 result_key TEXT, error_summary TEXT, requested_by UUID REFERENCES users(id),
 started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id) ON DELETE CASCADE,
 FOREIGN KEY(tenant_id,dataset_id) REFERENCES datasets(tenant_id,id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS audit_events (
 id BIGSERIAL PRIMARY KEY, tenant_id UUID, user_id UUID, action TEXT NOT NULL,
 resource_type TEXT NOT NULL, resource_id TEXT, details JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_projects_tenant ON projects(tenant_id);
CREATE INDEX IF NOT EXISTS idx_datasets_project ON datasets(tenant_id,project_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_status ON analysis_runs(tenant_id,status,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(tenant_id,created_at DESC);

-- Project-scoped analysis settings and immutable configuration snapshots.
CREATE TABLE IF NOT EXISTS project_settings (
 tenant_id UUID NOT NULL, project_id UUID NOT NULL, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 species_scope TEXT NOT NULL, payload JSONB NOT NULL DEFAULT '{}'::jsonb, updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant_id,project_id,user_id,species_scope),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS project_settings_history (
 snapshot_id TEXT PRIMARY KEY, tenant_id UUID NOT NULL, project_id UUID NOT NULL,
 user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, species_scope TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), fingerprint TEXT NOT NULL, payload JSONB NOT NULL,
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_project_settings_history_scope
 ON project_settings_history(tenant_id,project_id,user_id,species_scope,created_at DESC);

-- RLS applies to all tenant-owned resources. App DB role must not own tables or BYPASSRLS.
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;
ALTER TABLE project_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE datasets FORCE ROW LEVEL SECURITY;
ALTER TABLE analysis_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_runs FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
ALTER TABLE project_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_settings FORCE ROW LEVEL SECURITY;
ALTER TABLE project_settings_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_settings_history FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_projects ON projects USING(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid) WITH CHECK(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid);
CREATE POLICY tenant_project_memberships ON project_memberships USING(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid) WITH CHECK(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid);
CREATE POLICY tenant_datasets ON datasets USING(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid) WITH CHECK(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid);
CREATE POLICY tenant_runs ON analysis_runs USING(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid) WITH CHECK(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid);
CREATE POLICY tenant_audit ON audit_events USING(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid) WITH CHECK(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid);
CREATE POLICY tenant_project_settings ON project_settings USING(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid) WITH CHECK(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid);
CREATE POLICY tenant_project_settings_history ON project_settings_history USING(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid) WITH CHECK(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid);

-- Immutable project lifecycle snapshots (metadata and dataset manifest; dataset bytes remain in S3).
CREATE TABLE IF NOT EXISTS project_versions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL, project_id UUID NOT NULL,
 version_number INTEGER NOT NULL, snapshot_json JSONB NOT NULL,
 created_by UUID REFERENCES users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id) ON DELETE CASCADE,
 UNIQUE(tenant_id,project_id,version_number)
);
ALTER TABLE project_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_versions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_project_versions ON project_versions USING(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid) WITH CHECK(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid);
CREATE INDEX IF NOT EXISTS idx_project_versions ON project_versions(tenant_id,project_id,version_number DESC);
