import io, json, zipfile, hashlib
import pytest
from platform_core.project_archive import inspect_project_archive, ARCHIVE_FORMAT, ARCHIVE_VERSION


def _archive(data=b"parquet-placeholder"):
    manifest = {
        "format": ARCHIVE_FORMAT, "archive_version": ARCHIVE_VERSION,
        "project": {"name": "Test project", "species": "sheep", "description": ""},
        "datasets": [{"path": "datasets/0001.parquet", "species": "sheep", "sha256": hashlib.sha256(data).hexdigest(), "row_count": 1, "column_count": 2}],
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("datasets/0001.parquet", data)
    return out.getvalue()


def test_project_archive_manifest_and_hash_validate():
    result = inspect_project_archive(_archive())
    assert result["project"]["name"] == "Test project"
    assert len(result["datasets"]) == 1


def test_project_archive_rejects_tampered_dataset():
    payload = _archive(b"original")
    with zipfile.ZipFile(io.BytesIO(payload), "r") as source:
        manifest = json.loads(source.read("manifest.json"))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as target:
        target.writestr("manifest.json", json.dumps(manifest))
        target.writestr("datasets/0001.parquet", b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        inspect_project_archive(out.getvalue())


def test_project_archive_rejects_path_traversal():
    data = b"x"
    manifest = {"format": ARCHIVE_FORMAT, "archive_version": ARCHIVE_VERSION, "project": {"name": "P", "species": "sheep"}, "datasets": [{"path": "../evil.parquet", "species": "sheep", "sha256": hashlib.sha256(data).hexdigest()}]}
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("../evil.parquet", data)
    with pytest.raises(ValueError, match="unsafe"):
        inspect_project_archive(out.getvalue())
