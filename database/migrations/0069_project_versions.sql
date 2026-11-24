-- Release 6.9.0 migration: immutable project metadata/dataset-manifest checkpoints.
CREATE TABLE IF NOT EXISTS project_versions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 tenant_id UUID NOT NULL,
 project_id UUID NOT NULL,
 version_number INTEGER NOT NULL,
 snapshot_json JSONB NOT NULL,
 created_by UUID REFERENCES users(id),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id) ON DELETE CASCADE,
 UNIQUE(tenant_id,project_id,version_number)
);
ALTER TABLE project_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_versions FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname=current_schema() AND tablename='project_versions' AND policyname='tenant_project_versions') THEN
  CREATE POLICY tenant_project_versions ON project_versions
   USING(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid)
   WITH CHECK(tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid);
 END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_project_versions ON project_versions(tenant_id,project_id,version_number DESC);
