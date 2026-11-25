import os
import pytest
from platform_core import storage


def test_storage_backend_defaults_to_local_without_cloud_configuration(monkeypatch):
    monkeypatch.delenv('PROJECT_STORAGE_BACKEND', raising=False)
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('S3_BUCKET', raising=False)
    assert storage.backend_name() == 'local'


def test_storage_backend_rejects_incomplete_cloud_configuration(monkeypatch):
    monkeypatch.setenv('PROJECT_STORAGE_BACKEND', 'cloud')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('S3_BUCKET', raising=False)
    with pytest.raises(RuntimeError, match='Cloud storage requires'):
        storage.backend_name()


def test_storage_facade_delegates_to_local_backend(monkeypatch, tmp_path):
    monkeypatch.setenv('PROJECT_STORAGE_BACKEND', 'local')
    monkeypatch.setenv('LOCAL_PROJECT_STORAGE_DIR', str(tmp_path))
    # Reload local module so its database path reflects this isolated test directory.
    import importlib
    import platform_core.local_workspace as local_workspace
    importlib.reload(local_workspace)
    importlib.reload(storage)
    project_id = storage.create_project('tenant-test', 'user-test', 'Test project', 'sheep')
    projects = storage.list_projects('tenant-test', 'user-test')
    assert any(p['id'] == project_id for p in projects)
