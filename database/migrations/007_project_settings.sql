-- Durable tenant/project/user-scoped model settings for the PostgreSQL backend.
CREATE TABLE IF NOT EXISTS project_settings (
    tenant_id UUID NOT NULL,
    project_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    species_scope TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, project_id, user_id, species_scope),
    FOREIGN KEY (tenant_id, project_id) REFERENCES projects(tenant_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS project_settings_history (
    snapshot_id TEXT PRIMARY KEY,
    tenant_id UUID NOT NULL,
    project_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    species_scope TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    fingerprint TEXT NOT NULL,
    payload JSONB NOT NULL,
    FOREIGN KEY (tenant_id, project_id) REFERENCES projects(tenant_id, id) ON DELETE CASCADE
);

ALTER TABLE project_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_settings FORCE ROW LEVEL SECURITY;
ALTER TABLE project_settings_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_settings_history FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_project_settings ON project_settings;
CREATE POLICY tenant_project_settings ON project_settings
USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

DROP POLICY IF EXISTS tenant_project_settings_history ON project_settings_history;
CREATE POLICY tenant_project_settings_history ON project_settings_history
USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE INDEX IF NOT EXISTS idx_project_settings_history_scope
ON project_settings_history(tenant_id, project_id, user_id, species_scope, created_at DESC);
