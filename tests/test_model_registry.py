import hashlib
import pytest
from analysis_engine import model_registry as reg


def test_register_list_and_read_artifact_scoped_by_user(tmp_path, monkeypatch):
    monkeypatch.setenv("ANALYSIS_REGISTRY_PATH", str(tmp_path / "registry.sqlite3"))
    monkeypatch.setenv("MODEL_REGISTRY_DIR", str(tmp_path / "models"))
    payload = b"test-artifact-bytes"
    item = reg.register_model_artifact(payload=payload, model_name="Extra Trees methane",
        model_family="Extra Trees", task_type="regression", outcome="CH4_g_day",
        features=["DMI", "BW"], user_scope="tenant:user1", project_scope="project-1",
        species_scope="cattle", group_column="animal_id", training_records=100,
        training_groups=20, validation_metrics={"rmse": 4.2})
    assert item["version"] == 1
    listed = reg.list_models("tenant:user1", include_all_projects=True)
    assert len(listed) == 1 and listed[0]["status"] == "candidate"
    assert reg.list_models("tenant:user2", include_all_projects=True) == []
    record, saved = reg.read_model_artifact(item["model_id"], 1, "tenant:user1")
    assert saved == payload
    assert record["artifact_sha256"] == hashlib.sha256(payload).hexdigest()
    assert reg.get_model(item["model_id"], 1, "tenant:user2") is None


def test_versions_are_immutable_and_lifecycle_is_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("ANALYSIS_REGISTRY_PATH", str(tmp_path / "registry.sqlite3"))
    monkeypatch.setenv("MODEL_REGISTRY_DIR", str(tmp_path / "models"))
    item = reg.register_model_artifact(payload=b"v1", model_name="model", model_family="OLS",
        task_type="regression", outcome="y", features=["x"], user_scope="u", project_scope="p",
        training_records=10, training_groups=5)
    v2 = reg.add_model_version(item["model_id"], payload=b"v2", user_scope="u", notes="updated fit")
    assert v2["version"] == 2
    assert reg.read_model_artifact(item["model_id"], 1, "u")[1] == b"v1"
    assert reg.read_model_artifact(item["model_id"], 2, "u")[1] == b"v2"
    reg.set_model_status(item["model_id"], 2, "u", "approved")
    assert reg.get_model(item["model_id"], 2, "u")["status"] == "approved"
    with pytest.raises(KeyError):
        reg.set_model_status(item["model_id"], 2, "another-user", "retired")


def test_invalid_registration_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("ANALYSIS_REGISTRY_PATH", str(tmp_path / "registry.sqlite3"))
    monkeypatch.setenv("MODEL_REGISTRY_DIR", str(tmp_path / "models"))
    with pytest.raises(ValueError):
        reg.register_model_artifact(payload=b"x", model_name="bad", model_family="OLS",
            task_type="regression", outcome="y", features=[], user_scope="u", project_scope="p",
            training_records=10, training_groups=5)
