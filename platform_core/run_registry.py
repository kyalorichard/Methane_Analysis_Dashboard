"""Local SQLite registry for analysis metadata; raw data are never stored here."""
from __future__ import annotations
import os, sqlite3, json
from pathlib import Path
from datetime import datetime, timezone

# A shared metadata database can be configured for settings, experiments and run history.
# Preserve the legacy run-registry path unless an administrator explicitly opts in.
def _db_path(db_path=None):
    if db_path is not None:
        return Path(db_path)
    # Explicit legacy path wins; otherwise METHANE_METADATA_DB unifies local metadata.
    return Path(os.environ.get("METHANE_METADATA_DB") or os.environ.get("METHANE_RUN_REGISTRY") or "data/methane_metadata.sqlite3")

DEFAULT_DB = _db_path()

def _connect(db_path=None):
    path=_db_path(db_path)
    path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(path,timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS analysis_runs (
      run_id TEXT PRIMARY KEY, created_utc TEXT NOT NULL, dataset_name TEXT,
      dataset_fingerprint TEXT, outcome TEXT, species TEXT, status TEXT NOT NULL,
      manifest_json TEXT NOT NULL, summary_json TEXT NOT NULL)""")
    con.commit()
    from platform_core.metadata_migrations import migrate_legacy_metadata
    migrate_legacy_metadata(path)
    return con

def save_run(run_id, manifest, summary, status="completed", db_path=None):
    created=manifest.get("run_timestamp_utc") or datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as con:
        con.execute("INSERT OR REPLACE INTO analysis_runs VALUES (?,?,?,?,?,?,?,?,?)",(
          run_id,created,manifest.get("dataset_name"),manifest.get("audit",{}).get("data_sha256"),
          manifest.get("outcome"),manifest.get("species"),status,
          json.dumps(manifest,default=str,sort_keys=True),json.dumps(summary,default=str,sort_keys=True)))

def list_runs(limit=100, db_path=None):
    with _connect(db_path) as con:
        rows=con.execute("SELECT run_id,created_utc,dataset_name,dataset_fingerprint,outcome,species,status,manifest_json,summary_json FROM analysis_runs ORDER BY created_utc DESC LIMIT ?",(int(limit),)).fetchall()
    cols=["run_id","created_utc","dataset_name","dataset_fingerprint","outcome","species","status","manifest_json","summary_json"]
    return [dict(zip(cols,r)) for r in rows]

def delete_run(run_id, db_path=None):
    with _connect(db_path) as con: con.execute("DELETE FROM analysis_runs WHERE run_id=?",(run_id,))
