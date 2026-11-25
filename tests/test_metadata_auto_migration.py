import sqlite3
from pathlib import Path

from platform_core.metadata_migrations import migrate_legacy_metadata


def test_legacy_settings_experiments_and_runs_migrate_with_backup(tmp_path, monkeypatch):
    dest = tmp_path / "canonical.sqlite3"
    legacy_settings = tmp_path / "legacy_settings.sqlite3"
    legacy_runs = tmp_path / "legacy_runs.sqlite3"
    with sqlite3.connect(legacy_settings) as con:
        con.execute("CREATE TABLE scoped_settings (user_scope TEXT NOT NULL, project_scope TEXT NOT NULL, species_scope TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(user_scope,project_scope,species_scope))")
        con.execute("INSERT INTO scoped_settings VALUES ('u','p','sheep','{}','2026-01-01')")
        con.execute("CREATE TABLE experiments (experiment_id TEXT PRIMARY KEY, user_scope TEXT NOT NULL, project_scope TEXT NOT NULL, species_scope TEXT NOT NULL, experiment_name TEXT NOT NULL, created_at TEXT NOT NULL, config_json TEXT NOT NULL, metrics_json TEXT NOT NULL, paired_json TEXT NOT NULL, metadata_json TEXT NOT NULL)")
        con.execute("INSERT INTO experiments VALUES ('e1','u','p','sheep','exp','2026-01-01','{}','{}','[]','{}')")
    with sqlite3.connect(legacy_runs) as con:
        con.execute("CREATE TABLE analysis_runs (run_id TEXT PRIMARY KEY, created_utc TEXT NOT NULL, dataset_name TEXT, dataset_fingerprint TEXT, outcome TEXT, species TEXT, status TEXT NOT NULL, manifest_json TEXT NOT NULL, summary_json TEXT NOT NULL)")
        con.execute("INSERT INTO analysis_runs VALUES ('r1','2026-01-01','d','hash','methane','sheep','completed','{}','{}')")
    monkeypatch.setenv("METHANE_METADATA_DB", str(dest))
    monkeypatch.setenv("ANALYSIS_REGISTRY_PATH", str(legacy_settings))
    monkeypatch.setenv("METHANE_RUN_REGISTRY", str(legacy_runs))
    monkeypatch.setenv("LOCAL_WORKSPACE_DB", str(tmp_path / "absent_workspace.sqlite3"))
    report = migrate_legacy_metadata(dest)
    assert not report["errors"]
    with sqlite3.connect(dest) as con:
        assert con.execute("SELECT COUNT(*) FROM scoped_settings").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM experiments").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0] == 1
    assert len(report["backups"]) == 2
    # Idempotent: second run skips already-migrated sources.
    second = migrate_legacy_metadata(dest)
    assert second["sources"] == []
