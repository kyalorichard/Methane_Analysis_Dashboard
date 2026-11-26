import json
import uuid
import pandas as pd


def test_run_artifact_roundtrip_preserves_dataset_tables_manifest_and_figure():
    from analysis_engine.run_artifacts import build_run_artifact, read_run_artifact
    run_id = str(uuid.uuid4())
    frame = pd.DataFrame({"animal_id": ["A", "B", "C"], "methane": [1.2, 2.3, 1.8]})
    result = {
        "manifest": {"run_id": run_id, "dataset_name": "trial.csv", "dataset_fingerprint_sha256": "abc"},
        "summary": {"outcome": "methane", "scientific_caveats": ["interpret cautiously"]},
        "tables": {"quality_control": pd.DataFrame({"check": ["missing"], "value": [0]}),
                   "associations": pd.DataFrame(columns=["covariate", "r"])},
    }
    payload = build_run_artifact(result, dataset=frame, figure_html="<html><body>saved figure</body></html>")
    restored = read_run_artifact(payload)
    assert restored["manifest"]["run_id"] == run_id
    assert restored["summary"]["outcome"] == "methane"
    assert restored["tables"]["quality_control"].iloc[0]["value"] == 0
    assert restored["dataset"].shape == frame.shape
    assert restored["dataset"]["animal_id"].tolist() == ["A", "B", "C"]
    assert "saved figure" in restored["figure_html"]


def test_local_run_artifact_persistence_is_project_and_user_scoped(tmp_path, monkeypatch):
    from platform_core import local_workspace
    from platform_core.run_registry import save_run, save_run_artifact, load_run_artifact, list_runs
    from analysis_engine.run_artifacts import build_run_artifact, read_run_artifact
    db = tmp_path / "metadata.sqlite3"
    monkeypatch.setenv("METHANE_METADATA_DB", str(db))
    monkeypatch.setenv("LOCAL_PROJECT_STORAGE_DIR", str(tmp_path / "workspace"))
    monkeypatch.setenv("METHANE_RUN_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    local_workspace.ROOT = tmp_path / "workspace"
    tenant, subject = "tenant-1", "researcher@example.org"
    project_id = local_workspace.create_project(tenant, subject, "Trial", "sheep")
    run_id = str(uuid.uuid4())
    manifest = {"run_timestamp_utc": "2026-11-26T00:00:00+00:00", "dataset_name": "trial.csv", "species": "sheep"}
    save_run(run_id, manifest, {"n": 3}, db_path=db, tenant_id=tenant, project_id=project_id, user_subject=subject)
    payload = build_run_artifact({"manifest": {"run_id": run_id}, "summary": {"n": 3},
        "tables": {"summary_table": pd.DataFrame({"n": [3]})}}, dataset=pd.DataFrame({"x": [1, 2, 3]}))
    save_run_artifact(run_id, payload, tenant_id=tenant, project_id=project_id, user_subject=subject, db_path=db)
    loaded = load_run_artifact(run_id, tenant_id=tenant, project_id=project_id, user_subject=subject, db_path=db)
    assert read_run_artifact(loaded)["dataset"]["x"].tolist() == [1, 2, 3]
    assert list_runs(db_path=db, tenant_id=tenant, project_id=project_id, user_subject=subject)[0]["artifact_available"]
    artifact_path = list_runs(db_path=db, tenant_id=tenant, project_id=project_id, user_subject=subject)[0]["artifact_key"]
    with open(artifact_path, "ab") as handle:
        handle.write(b"tamper")
    import pytest
    with pytest.raises(IOError, match="checksum"):
        load_run_artifact(run_id, tenant_id=tenant, project_id=project_id, user_subject=subject, db_path=db)
    with pytest.raises(PermissionError):
        load_run_artifact(run_id, tenant_id=tenant, project_id=project_id, user_subject="another-user", db_path=db)


def test_project_archive_roundtrip_includes_reopenable_analysis_artifacts(tmp_path, monkeypatch):
    from platform_core import local_workspace
    from platform_core.run_registry import save_run, save_run_artifact, list_runs, load_run_artifact
    from platform_core.project_archive import build_project_archive, import_project_archive, inspect_project_archive
    from analysis_engine.run_artifacts import build_run_artifact, read_run_artifact
    db = tmp_path / "archive-metadata.sqlite3"
    monkeypatch.setenv("METHANE_METADATA_DB", str(db))
    monkeypatch.setenv("METHANE_RUN_ARTIFACT_DIR", str(tmp_path / "archive-artifacts"))
    monkeypatch.setenv("PROJECT_STORAGE_BACKEND", "local")
    local_workspace.ROOT = tmp_path / "archive-workspace"
    tenant, subject = "tenant-archive", "archive-user"
    source_project = local_workspace.create_project(tenant, subject, "Source", "sheep")
    run_id = str(uuid.uuid4())
    run_manifest = {"run_timestamp_utc": "2026-11-26T00:00:00+00:00", "dataset_name": "source.csv", "species": "sheep"}
    save_run(run_id, run_manifest, {"n": 2}, tenant_id=tenant, project_id=source_project, user_subject=subject)
    data = pd.DataFrame({"methane": [1.0, 2.0]})
    artifact = build_run_artifact({"manifest": {"run_id": run_id, "dataset_name": "source.csv"},
        "summary": {"n": 2}, "tables": {"descriptive_statistics": pd.DataFrame({"mean": [1.5]})}}, dataset=data)
    save_run_artifact(run_id, artifact, tenant_id=tenant, project_id=source_project, user_subject=subject)
    archive = build_project_archive(tenant, subject, source_project)
    checked = inspect_project_archive(archive)
    assert len(checked["analysis_runs"]) == 1
    imported = import_project_archive(archive, tenant, subject, project_name="Imported")
    restored_runs = list_runs(tenant_id=tenant, project_id=imported["project_id"], user_subject=subject)
    assert len(restored_runs) == 1
    assert restored_runs[0]["artifact_available"]
    restored = read_run_artifact(load_run_artifact(restored_runs[0]["run_id"], tenant_id=tenant,
        project_id=imported["project_id"], user_subject=subject))
    assert restored["dataset"]["methane"].tolist() == [1.0, 2.0]
    assert restored["manifest"]["imported_from_run_id"] == run_id
