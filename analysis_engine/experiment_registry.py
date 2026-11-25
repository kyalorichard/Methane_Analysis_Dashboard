"""Persistent, scoped analysis settings and experiment registry (SQLite)."""
from __future__ import annotations
import json, os, sqlite3, hashlib
from contextlib import closing
from pathlib import Path
from datetime import datetime, timezone


def _db_path():
    path = Path(os.getenv("METHANE_METADATA_DB") or os.getenv("ANALYSIS_REGISTRY_PATH") or "data/methane_metadata.sqlite3")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect():
    con = sqlite3.connect(str(_db_path()), timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS scoped_settings (
        user_scope TEXT NOT NULL, project_scope TEXT NOT NULL, species_scope TEXT NOT NULL,
        payload TEXT NOT NULL, updated_at TEXT NOT NULL,
        PRIMARY KEY(user_scope, project_scope, species_scope))""")
    con.execute("""CREATE TABLE IF NOT EXISTS experiments (
        experiment_id TEXT PRIMARY KEY, user_scope TEXT NOT NULL, project_scope TEXT NOT NULL,
        species_scope TEXT NOT NULL, experiment_name TEXT NOT NULL, created_at TEXT NOT NULL,
        config_json TEXT NOT NULL, metrics_json TEXT NOT NULL, paired_json TEXT NOT NULL,
        metadata_json TEXT NOT NULL)""")
    # Initialise history during every connection bootstrap. The Settings page
    # reads history before a user necessarily creates their first snapshot.
    con.execute("""CREATE TABLE IF NOT EXISTS settings_history (
        snapshot_id TEXT PRIMARY KEY, user_scope TEXT NOT NULL, project_scope TEXT NOT NULL,
        species_scope TEXT NOT NULL, created_at TEXT NOT NULL, fingerprint TEXT NOT NULL,
        payload TEXT NOT NULL)""")
    con.execute("""CREATE INDEX IF NOT EXISTS idx_settings_history_scope_time
        ON settings_history(user_scope, project_scope, species_scope, created_at DESC)""")
    con.commit()
    # Import legacy settings/experiment metadata once into the canonical local store.
    from platform_core.metadata_migrations import migrate_legacy_metadata
    migrate_legacy_metadata(_db_path())
    return con


def save_settings(user_scope, project_scope, species_scope, settings):
    stamp = datetime.now(timezone.utc).isoformat()
    with closing(_connect()) as con:
        con.execute("INSERT INTO scoped_settings VALUES (?,?,?,?,?) ON CONFLICT(user_scope,project_scope,species_scope) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
                    (str(user_scope), str(project_scope), str(species_scope), json.dumps(settings, sort_keys=True), stamp))
        con.commit()
    return stamp


def load_settings(user_scope, project_scope, species_scope):
    with closing(_connect()) as con:
        row = con.execute("SELECT payload, updated_at FROM scoped_settings WHERE user_scope=? AND project_scope=? AND species_scope=?",
                          (str(user_scope), str(project_scope), str(species_scope))).fetchone()
    return (json.loads(row[0]), row[1]) if row else (None, None)


def save_experiment(user_scope, project_scope, species_scope, name, config, metrics, paired=None, metadata=None):
    stamp = datetime.now(timezone.utc).isoformat()
    raw = json.dumps([user_scope, project_scope, species_scope, name, stamp, config, metrics, paired or [], metadata or {}], sort_keys=True, default=str)
    exp_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
    with closing(_connect()) as con:
        con.execute("INSERT OR REPLACE INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?)",
            (exp_id, str(user_scope), str(project_scope), str(species_scope), str(name), stamp,
             json.dumps(config, sort_keys=True, default=str), json.dumps(metrics, default=str),
             json.dumps(paired or [], default=str), json.dumps(metadata or {}, default=str)))
        con.commit()
    return exp_id


def list_experiments(user_scope, project_scope=None, species_scope=None, limit=100):
    clauses=["user_scope=?"]; params=[str(user_scope)]
    if project_scope is not None: clauses.append("project_scope=?"); params.append(str(project_scope))
    if species_scope is not None: clauses.append("species_scope=?"); params.append(str(species_scope))
    params.append(int(limit))
    with closing(_connect()) as con:
        rows=con.execute("SELECT experiment_id,project_scope,species_scope,experiment_name,created_at,metrics_json,metadata_json FROM experiments WHERE "+" AND ".join(clauses)+" ORDER BY created_at DESC LIMIT ?",params).fetchall()
    return [{"experiment_id":r[0],"project_scope":r[1],"species_scope":r[2],"experiment_name":r[3],"created_at":r[4],"metrics":json.loads(r[5]),"metadata":json.loads(r[6])} for r in rows]


def get_experiment(experiment_id, user_scope):
    with closing(_connect()) as con:
        row=con.execute("SELECT project_scope,species_scope,experiment_name,created_at,config_json,metrics_json,paired_json,metadata_json FROM experiments WHERE experiment_id=? AND user_scope=?",(str(experiment_id),str(user_scope))).fetchone()
    if not row: return None
    return {"project_scope":row[0],"species_scope":row[1],"experiment_name":row[2],"created_at":row[3],"config":json.loads(row[4]),"metrics":json.loads(row[5]),"paired_comparisons":json.loads(row[6]),"metadata":json.loads(row[7])}


def export_project_state(user_scope, project_scope):
    """Export local settings and experiment metadata for one user/project scope."""
    with closing(_connect()) as con:
        settings = con.execute(
            "SELECT species_scope,payload,updated_at FROM scoped_settings WHERE user_scope=? AND project_scope=?",
            (str(user_scope), str(project_scope)),
        ).fetchall()
        experiments = con.execute(
            "SELECT species_scope,experiment_name,created_at,config_json,metrics_json,paired_json,metadata_json FROM experiments WHERE user_scope=? AND project_scope=? ORDER BY created_at",
            (str(user_scope), str(project_scope)),
        ).fetchall()
    return {
        "settings": [{"species_scope": r[0], "payload": json.loads(r[1]), "updated_at": r[2]} for r in settings],
        "experiments": [{"species_scope": r[0], "name": r[1], "created_at": r[2], "config": json.loads(r[3]), "metrics": json.loads(r[4]), "paired_comparisons": json.loads(r[5]), "metadata": json.loads(r[6])} for r in experiments],
    }


def import_project_state(user_scope, project_scope, state):
    """Restore portable settings and experiment metadata under the destination scope."""
    stamp = datetime.now(timezone.utc).isoformat()
    with closing(_connect()) as con:
        for item in state.get("settings", []):
            con.execute(
                "INSERT INTO scoped_settings VALUES (?,?,?,?,?) ON CONFLICT(user_scope,project_scope,species_scope) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at",
                (str(user_scope), str(project_scope), str(item.get("species_scope", "all")), json.dumps(item.get("payload", {}), sort_keys=True), stamp),
            )
        for item in state.get("experiments", []):
            save_experiment(user_scope, project_scope, item.get("species_scope", "all"), item.get("name", "Imported experiment"), item.get("config", {}), item.get("metrics", {}), item.get("paired_comparisons", []), {**(item.get("metadata") or {}), "imported_from_archive": True, "original_created_at": item.get("created_at")})
        con.commit()


def save_settings_snapshot(user_scope, project_scope, species_scope, settings):
    """Append an immutable, fingerprinted configuration snapshot for auditability."""
    from analysis_engine.settings_config import config_fingerprint
    stamp = datetime.now(timezone.utc).isoformat()
    fingerprint = config_fingerprint(settings)
    snapshot_id = hashlib.sha256(f"{user_scope}|{project_scope}|{species_scope}|{stamp}|{fingerprint}".encode()).hexdigest()[:20]
    with closing(_connect()) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS settings_history (
            snapshot_id TEXT PRIMARY KEY, user_scope TEXT NOT NULL, project_scope TEXT NOT NULL,
            species_scope TEXT NOT NULL, created_at TEXT NOT NULL, fingerprint TEXT NOT NULL,
            payload TEXT NOT NULL)""")
        con.execute("INSERT INTO settings_history VALUES (?,?,?,?,?,?,?)", (snapshot_id, str(user_scope), str(project_scope), str(species_scope), stamp, fingerprint, json.dumps(settings, sort_keys=True, default=str)))
        con.commit()
    return {"snapshot_id": snapshot_id, "created_at": stamp, "fingerprint": fingerprint}


def list_settings_snapshots(user_scope, project_scope, species_scope=None, limit=20):
    with closing(_connect()) as con:
        query = "SELECT snapshot_id, species_scope, created_at, fingerprint FROM settings_history WHERE user_scope=? AND project_scope=?"
        params = [str(user_scope), str(project_scope)]
        if species_scope is not None:
            query += " AND species_scope=?"; params.append(str(species_scope))
        query += " ORDER BY created_at DESC LIMIT ?"; params.append(int(limit))
        rows = con.execute(query, params).fetchall()
    return [{"snapshot_id": r[0], "species_scope": r[1], "created_at": r[2], "fingerprint": r[3]} for r in rows]
