import importlib
import sqlite3


def test_shared_metadata_db_hosts_workspace_settings_experiments_and_runs(monkeypatch, tmp_path):
    db = tmp_path / "unified_metadata.sqlite3"
    monkeypatch.setenv("METHANE_METADATA_DB", str(db))
    monkeypatch.delenv("ANALYSIS_REGISTRY_PATH", raising=False)
    monkeypatch.delenv("METHANE_RUN_REGISTRY", raising=False)
    monkeypatch.setenv("LOCAL_PROJECT_STORAGE_DIR", str(tmp_path / "workspace_files"))
    monkeypatch.delenv("LOCAL_WORKSPACE_DB", raising=False)

    from analysis_engine import experiment_registry
    from platform_core import run_registry, local_workspace
    importlib.reload(experiment_registry)
    importlib.reload(run_registry)
    importlib.reload(local_workspace)

    local_workspace._connect().close()
    experiment_registry.save_settings("u1", "p1", "sheep", {"alpha": 0.05})
    experiment_registry.save_settings_snapshot("u1", "p1", "sheep", {"alpha": 0.05})
    run_registry.save_run("r1", {"species": "sheep"}, {"score": 0.8})

    with sqlite3.connect(db) as con:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"projects", "datasets", "versions", "scoped_settings", "settings_history", "experiments", "analysis_runs"} <= tables
