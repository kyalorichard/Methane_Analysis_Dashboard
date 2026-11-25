import json


def test_settings_history_table_exists_before_first_snapshot(tmp_path, monkeypatch):
    from analysis_engine import experiment_registry as registry

    db_path = tmp_path / "registry.sqlite3"
    monkeypatch.setenv("ANALYSIS_REGISTRY_PATH", str(db_path))

    # This is the first registry operation: history must be an empty list,
    # not an OperationalError because the table has not yet been created.
    assert registry.list_settings_snapshots("user-1", "project-1", "cattle", 20) == []

    snapshot = registry.save_settings_snapshot(
        "user-1", "project-1", "cattle", {"alpha": 0.05, "seed": 42}
    )
    rows = registry.list_settings_snapshots("user-1", "project-1", "cattle", 20)
    assert len(rows) == 1
    assert rows[0]["snapshot_id"] == snapshot["snapshot_id"]
    assert rows[0]["fingerprint"] == snapshot["fingerprint"]


def test_settings_history_is_scoped_by_user_project_and_species(tmp_path, monkeypatch):
    from analysis_engine import experiment_registry as registry

    monkeypatch.setenv("ANALYSIS_REGISTRY_PATH", str(tmp_path / "registry.sqlite3"))
    registry.save_settings_snapshot("u1", "p1", "cattle", {"x": 1})
    registry.save_settings_snapshot("u1", "p1", "sheep", {"x": 2})
    registry.save_settings_snapshot("u2", "p1", "cattle", {"x": 3})

    assert len(registry.list_settings_snapshots("u1", "p1", "cattle")) == 1
    assert len(registry.list_settings_snapshots("u1", "p1", None)) == 2
    assert registry.list_settings_snapshots("u2", "p1", "cattle")[0]["species_scope"] == "cattle"
