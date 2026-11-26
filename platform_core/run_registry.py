"""Tenant/project-scoped analysis run metadata for local and cloud workspaces.

The registry stores run metadata and artifact pointers. Result tables, input snapshots and
figures are stored as separate integrity-checked project artifacts.
"""
from __future__ import annotations
import json
import os
import sqlite3
import hashlib
import uuid
from pathlib import Path
from datetime import datetime, timezone


def _db_path(db_path=None):
    if db_path is not None:
        return Path(db_path)
    return Path(os.environ.get("METHANE_METADATA_DB") or os.environ.get("METHANE_RUN_REGISTRY") or "data/methane_metadata.sqlite3")


def _uses_cloud_backend(db_path=None):
    if db_path is not None:
        return False
    from platform_core.storage import backend_name
    return backend_name() == "cloud"


def _connect(db_path=None):
    path = _db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS analysis_runs (
      run_id TEXT PRIMARY KEY, created_utc TEXT NOT NULL, dataset_name TEXT,
      dataset_fingerprint TEXT, outcome TEXT, species TEXT, status TEXT NOT NULL,
      manifest_json TEXT NOT NULL, summary_json TEXT NOT NULL,
      tenant_id TEXT, project_id TEXT, user_subject TEXT, dataset_id TEXT,
      module_key TEXT NOT NULL DEFAULT 'integrated_analysis', artifact_key TEXT, artifact_sha256 TEXT)""")
    existing = {r[1] for r in con.execute("PRAGMA table_info(analysis_runs)")}
    additions = {
        "tenant_id": "TEXT", "project_id": "TEXT", "user_subject": "TEXT",
        "dataset_id": "TEXT", "module_key": "TEXT NOT NULL DEFAULT 'integrated_analysis'", "artifact_key": "TEXT", "artifact_sha256": "TEXT",
    }
    for name, definition in additions.items():
        if name not in existing:
            con.execute(f"ALTER TABLE analysis_runs ADD COLUMN {name} {definition}")
    con.execute("CREATE INDEX IF NOT EXISTS idx_analysis_runs_scope ON analysis_runs(tenant_id,user_subject,project_id,created_utc DESC)")
    con.commit()
    from platform_core.metadata_migrations import migrate_legacy_metadata
    migrate_legacy_metadata(path)
    return con


def _decode_row(row):
    return {
        "run_id": row[0], "created_utc": row[1], "dataset_name": row[2],
        "dataset_fingerprint": row[3], "outcome": row[4], "species": row[5],
        "status": row[6], "manifest_json": row[7], "summary_json": row[8],
        "tenant_id": row[9], "project_id": row[10], "user_subject": row[11],
        "dataset_id": row[12], "module_key": row[13], "artifact_key": row[14],
        "artifact_available": bool(row[14]), "artifact_sha256": row[15],
    }


def _cloud_save(run_id, manifest, summary, status, tenant_id, project_id, dataset_id, user_subject, module_key):
    if not tenant_id or not project_id or not user_subject:
        raise ValueError("Cloud analysis history requires an active tenant, project and authenticated user. Open or create a project before saving this run.")
    from sqlalchemy import text
    from platform_core.database import tenant_session
    from platform_core.workspace import _user_id, _assert_project_access
    params = {
        "manifest": manifest, "summary": summary,
        "dataset_name": manifest.get("dataset_name"),
        "dataset_fingerprint": manifest.get("dataset_fingerprint_sha256") or manifest.get("audit", {}).get("data_sha256"),
        "outcome": manifest.get("outcome"), "species": manifest.get("species"),
    }
    created = manifest.get("run_timestamp_utc") or datetime.now(timezone.utc).isoformat()
    db_status = "succeeded" if status in {"completed", "succeeded"} else status
    if db_status not in {"queued", "running", "succeeded", "failed", "cancelled"}:
        db_status = "failed"
    with tenant_session(tenant_id) as session:
        uid = _user_id(session, user_subject)
        _assert_project_access(session, tenant_id, project_id, uid, write=True)
        session.execute(text("""INSERT INTO analysis_runs
          (id,tenant_id,project_id,dataset_id,module_key,parameters,status,requested_by,started_at,completed_at,created_at)
          VALUES (CAST(:id AS uuid),CAST(:tenant AS uuid),CAST(:project AS uuid),
          CAST(:dataset AS uuid),:module,CAST(:parameters AS jsonb),:status,CAST(:uid AS uuid),
          CAST(:created AS timestamptz),CAST(:created AS timestamptz),CAST(:created AS timestamptz))
          ON CONFLICT (id) DO UPDATE SET parameters=EXCLUDED.parameters,status=EXCLUDED.status,
          completed_at=EXCLUDED.completed_at"""), {
            "id": str(run_id), "tenant": tenant_id, "project": project_id,
            "dataset": dataset_id or None, "module": module_key,
            "parameters": json.dumps(params, default=str), "status": db_status,
            "uid": uid, "created": created,
        })
        session.execute(text("""INSERT INTO audit_events(tenant_id,user_id,action,resource_type,resource_id,details)
          VALUES (CAST(:tenant AS uuid),CAST(:uid AS uuid),'analysis_run.saved','analysis_run',:run_id,CAST(:details AS jsonb))"""), {
            "tenant": tenant_id, "uid": uid, "run_id": str(run_id),
            "details": json.dumps({"project_id": project_id, "dataset_id": dataset_id, "module_key": module_key, "status": db_status}),
        })


def save_run(run_id, manifest, summary, status="completed", db_path=None, *,
             tenant_id=None, project_id=None, dataset_id=None, user_subject=None,
             module_key="integrated_analysis"):
    created = manifest.get("run_timestamp_utc") or datetime.now(timezone.utc).isoformat()
    if _uses_cloud_backend(db_path):
        return _cloud_save(run_id, manifest, summary, status, tenant_id, project_id, dataset_id, user_subject, module_key)
    with _connect(db_path) as con:
        con.execute("""INSERT OR REPLACE INTO analysis_runs
          (run_id,created_utc,dataset_name,dataset_fingerprint,outcome,species,status,
           manifest_json,summary_json,tenant_id,project_id,user_subject,dataset_id,module_key)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(run_id), created, manifest.get("dataset_name"),
            manifest.get("dataset_fingerprint_sha256") or manifest.get("audit", {}).get("data_sha256"),
            manifest.get("outcome"), manifest.get("species"), status,
            json.dumps(manifest, default=str, sort_keys=True), json.dumps(summary, default=str, sort_keys=True),
            tenant_id, project_id, user_subject, dataset_id, module_key,
        ))
    return str(run_id)


def _cloud_list(limit, tenant_id, project_id, user_subject):
    if not tenant_id or not user_subject:
        return []
    from sqlalchemy import text
    from platform_core.database import tenant_session
    from platform_core.workspace import _user_id, _assert_project_access
    with tenant_session(tenant_id) as session:
        uid = _user_id(session, user_subject)
        if project_id:
            _assert_project_access(session, tenant_id, project_id, uid, write=False)
        rows = session.execute(text("""SELECT ar.id::text AS run_id,ar.created_at,ar.project_id::text,
          ar.dataset_id::text,ar.module_key,ar.status,ar.parameters,ar.result_key
          FROM analysis_runs ar WHERE ar.tenant_id=CAST(:tenant AS uuid)
          AND (:project IS NULL OR ar.project_id=CAST(:project AS uuid))
          AND (EXISTS (SELECT 1 FROM tenant_memberships tm WHERE tm.tenant_id=ar.tenant_id AND tm.user_id=CAST(:uid AS uuid) AND tm.role='tenant_admin')
            OR EXISTS (SELECT 1 FROM project_memberships pm WHERE pm.tenant_id=ar.tenant_id AND pm.project_id=ar.project_id AND pm.user_id=CAST(:uid AS uuid)))
          ORDER BY ar.created_at DESC LIMIT :limit"""), {
            "tenant": tenant_id, "project": project_id, "uid": uid, "limit": int(limit),
        }).mappings().all()
    output = []
    for row in rows:
        p = row.get("parameters") or {}
        manifest = p.get("manifest", {})
        summary = p.get("summary", {})
        output.append({
            "run_id": row["run_id"], "created_utc": row["created_at"].isoformat() if row["created_at"] else None,
            "dataset_name": p.get("dataset_name") or manifest.get("dataset_name"),
            "dataset_fingerprint": p.get("dataset_fingerprint"),
            "outcome": p.get("outcome") or manifest.get("outcome"),
            "species": p.get("species") or manifest.get("species"),
            "status": row["status"], "artifact_key": row.get("result_key"), "artifact_available": bool(row.get("result_key")), "manifest_json": json.dumps(manifest, default=str),
            "summary_json": json.dumps(summary, default=str), "tenant_id": tenant_id,
            "project_id": row["project_id"], "dataset_id": row["dataset_id"], "module_key": row["module_key"],
        })
    return output


def list_runs(limit=100, db_path=None, *, tenant_id=None, project_id=None, user_subject=None):
    if _uses_cloud_backend(db_path):
        return _cloud_list(limit, tenant_id, project_id, user_subject)
    query = "SELECT run_id,created_utc,dataset_name,dataset_fingerprint,outcome,species,status,manifest_json,summary_json,tenant_id,project_id,user_subject,dataset_id,module_key,artifact_key,artifact_sha256 FROM analysis_runs"
    clauses, args = [], []
    if tenant_id is not None:
        clauses.append("tenant_id=?"); args.append(tenant_id)
    if project_id is not None:
        clauses.append("project_id=?"); args.append(project_id)
    if user_subject is not None:
        clauses.append("user_subject=?"); args.append(user_subject)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_utc DESC LIMIT ?"; args.append(int(limit))
    with _connect(db_path) as con:
        rows = con.execute(query, args).fetchall()
    return [_decode_row(row) for row in rows]


def delete_run(run_id, db_path=None, *, tenant_id=None, project_id=None, user_subject=None):
    if _uses_cloud_backend(db_path):
        raise NotImplementedError("Cloud analysis-run deletion is not exposed through this registry yet.")
    clauses, args = ["run_id=?"], [str(run_id)]
    if tenant_id is not None: clauses.append("tenant_id=?"); args.append(tenant_id)
    if project_id is not None: clauses.append("project_id=?"); args.append(project_id)
    if user_subject is not None: clauses.append("user_subject=?"); args.append(user_subject)
    with _connect(db_path) as con:
        con.execute("DELETE FROM analysis_runs WHERE " + " AND ".join(clauses), args)



def _safe_run_id(run_id):
    try:
        return str(uuid.UUID(str(run_id)))
    except Exception as exc:
        raise ValueError("Invalid analysis run identifier.") from exc


def save_run_artifact(run_id, payload: bytes, *, tenant_id, project_id, user_subject, db_path=None):
    """Persist an immutable ZIP artifact under the owning project and attach it to the run."""
    if not tenant_id or not project_id or not user_subject:
        raise ValueError("Persistent analysis artifacts require an active project and authenticated user.")
    if not isinstance(payload, (bytes, bytearray)) or not payload:
        raise ValueError("A non-empty analysis artifact is required.")
    rid = _safe_run_id(run_id)
    digest = hashlib.sha256(payload).hexdigest()
    if _uses_cloud_backend(db_path):
        from sqlalchemy import text
        from platform_core.database import tenant_session
        from platform_core.workspace import _user_id, _assert_project_access
        import boto3
        key = f"tenants/{tenant_id}/projects/{project_id}/analysis-runs/{rid}/artifacts.zip"
        bucket = os.environ["S3_BUCKET"]
        client = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
        client.put_object(Bucket=bucket, Key=key, Body=bytes(payload), ContentType="application/zip",
                          ServerSideEncryption="aws:kms", Metadata={"sha256": digest, "run-id": rid})
        try:
            with tenant_session(tenant_id) as session:
                uid = _user_id(session, user_subject)
                _assert_project_access(session, tenant_id, project_id, uid, write=True)
                updated = session.execute(text("UPDATE analysis_runs SET result_key=:key WHERE id=CAST(:rid AS uuid) AND tenant_id=CAST(:tid AS uuid) AND project_id=CAST(:pid AS uuid) AND requested_by=CAST(:uid AS uuid)"),
                    {"key": key, "rid": rid, "tid": tenant_id, "pid": project_id, "uid": uid}).rowcount
                if not updated:
                    raise PermissionError("Analysis run is not available to this user in the active project.")
                session.execute(text("INSERT INTO audit_events(tenant_id,user_id,action,resource_type,resource_id,details) VALUES (CAST(:tid AS uuid),CAST(:uid AS uuid),'analysis_run.artifact_saved','analysis_run',:rid,CAST(:details AS jsonb))"),
                    {"tid": tenant_id, "uid": uid, "rid": rid, "details": json.dumps({"sha256": digest, "size_bytes": len(payload)})})
        except Exception:
            client.delete_object(Bucket=bucket, Key=key)
            raise
        return {"artifact_key": key, "sha256": digest, "size_bytes": len(payload)}

    with _connect(db_path) as con:
        row = con.execute("SELECT 1 FROM analysis_runs WHERE run_id=? AND tenant_id=? AND project_id=? AND user_subject=?", (rid, tenant_id, project_id, user_subject)).fetchone()
        if not row:
            raise PermissionError("Analysis run is not available to this user in the active project.")
        project = con.execute("SELECT 1 FROM projects WHERE id=? AND tenant_id=? AND owner=?", (project_id, tenant_id, user_subject)).fetchone()
        if not project:
            raise PermissionError("Project is not available in this local workspace.")
        root = Path(os.getenv("METHANE_RUN_ARTIFACT_DIR", "data/analysis_artifacts")).expanduser().resolve()
        target = root / "tenants" / str(tenant_id) / "projects" / str(project_id) / rid / "artifacts.zip"
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".zip.tmp")
        temp.write_bytes(bytes(payload)); os.replace(temp, target)
        con.execute("UPDATE analysis_runs SET artifact_key=?,artifact_sha256=? WHERE run_id=?", (str(target), digest, rid))
    return {"artifact_key": str(target), "sha256": digest, "size_bytes": len(payload)}


def load_run_artifact(run_id, *, tenant_id, project_id, user_subject, db_path=None):
    """Load an artifact only after rechecking the caller's project and run access."""
    rid = _safe_run_id(run_id)
    if not tenant_id or not project_id or not user_subject:
        raise PermissionError("An authenticated project context is required to reopen an analysis.")
    if _uses_cloud_backend(db_path):
        from sqlalchemy import text
        from platform_core.database import tenant_session
        from platform_core.workspace import _user_id, _assert_project_access
        import boto3
        with tenant_session(tenant_id) as session:
            uid = _user_id(session, user_subject)
            _assert_project_access(session, tenant_id, project_id, uid, write=False)
            row = session.execute(text("SELECT result_key FROM analysis_runs WHERE id=CAST(:rid AS uuid) AND tenant_id=CAST(:tid AS uuid) AND project_id=CAST(:pid AS uuid) AND (requested_by=CAST(:uid AS uuid) OR EXISTS (SELECT 1 FROM project_memberships pm WHERE pm.tenant_id=CAST(:tid AS uuid) AND pm.project_id=CAST(:pid AS uuid) AND pm.user_id=CAST(:uid AS uuid)))"),
                {"rid": rid, "tid": tenant_id, "pid": project_id, "uid": uid}).mappings().first()
        if not row or not row.get("result_key"):
            raise FileNotFoundError("No persisted result artifact is available for this analysis run.")
        obj = boto3.client("s3", region_name=os.getenv("AWS_REGION")).get_object(Bucket=os.environ["S3_BUCKET"], Key=row["result_key"])
        payload = obj["Body"].read()
        expected = (obj.get("Metadata") or {}).get("sha256")
        if expected and hashlib.sha256(payload).hexdigest() != expected:
            raise IOError("Stored analysis artifact checksum validation failed.")
        return payload

    with _connect(db_path) as con:
        row = con.execute("SELECT artifact_key,artifact_sha256 FROM analysis_runs WHERE run_id=? AND tenant_id=? AND project_id=? AND user_subject=?", (rid, tenant_id, project_id, user_subject)).fetchone()
        project = con.execute("SELECT 1 FROM projects WHERE id=? AND tenant_id=? AND owner=?", (project_id, tenant_id, user_subject)).fetchone()
    if not project:
        raise PermissionError("Project is not available in this local workspace.")
    if not row or not row[0]:
        raise FileNotFoundError("No persisted result artifact is available for this analysis run.")
    path = Path(row[0]).resolve()
    root = Path(os.getenv("METHANE_RUN_ARTIFACT_DIR", "data/analysis_artifacts")).expanduser().resolve()
    if root not in path.parents or not path.is_file():
        raise FileNotFoundError("Stored analysis artifact is missing or outside the configured artifact directory.")
    payload = path.read_bytes()
    if row[1] and hashlib.sha256(payload).hexdigest() != row[1]:
        raise IOError("Stored analysis artifact checksum validation failed.")
    return payload
