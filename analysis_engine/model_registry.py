"""Versioned, project-scoped registry for trusted scikit-learn model artifacts.

Artifacts use skops.io (never pickle/joblib). Metadata and artifact files are stored
locally; deployments with ephemeral filesystems need a persistent volume before
using this registry for durable production model governance.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def _db_path() -> Path:
    path = Path(os.getenv("ANALYSIS_REGISTRY_PATH") or os.getenv("METHANE_METADATA_DB") or "data/methane_metadata.sqlite3")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _artifact_root() -> Path:
    path = Path(os.getenv("MODEL_REGISTRY_DIR") or "data/model_registry")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _connect():
    con = sqlite3.connect(str(_db_path()), timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS registered_models (
        model_id TEXT NOT NULL, version INTEGER NOT NULL,
        user_scope TEXT NOT NULL, project_scope TEXT NOT NULL, species_scope TEXT NOT NULL,
        model_name TEXT NOT NULL, model_family TEXT NOT NULL, task_type TEXT NOT NULL,
        outcome TEXT NOT NULL, features_json TEXT NOT NULL, group_column TEXT,
        dataset_fingerprint TEXT, training_records INTEGER NOT NULL, training_groups INTEGER NOT NULL,
        random_seed INTEGER, validation_metrics_json TEXT NOT NULL, notes TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('candidate','approved','retired')),
        artifact_path TEXT NOT NULL, artifact_sha256 TEXT NOT NULL,
        created_at TEXT NOT NULL, approved_at TEXT,
        PRIMARY KEY(model_id, version))""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_registered_models_scope ON registered_models(user_scope, project_scope, created_at DESC)")
    con.commit()
    return con


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._")
    if not value:
        raise ValueError("Model name must contain at least one letter or number.")
    return value[:100]


def serialize_estimator(estimator) -> bytes:
    """Serialize with skops; pickle/joblib are intentionally not supported."""
    try:
        import skops.io as sio
    except ImportError as exc:
        raise RuntimeError("Safe model serialization requires skops. Install the project dependency: pip install skops.") from exc
    return sio.dumps(estimator)


def inspect_artifact(payload: bytes) -> list[str]:
    """Return non-default types skops requires the user to explicitly trust."""
    try:
        import skops.io as sio
    except ImportError as exc:
        raise RuntimeError("Safe model loading requires skops. Install the project dependency: pip install skops.") from exc
    return sorted(sio.get_untrusted_types(data=payload))


def deserialize_estimator(payload: bytes, trusted_types=None):
    """Load only after caller has explicitly supplied all untrusted type names."""
    try:
        import skops.io as sio
    except ImportError as exc:
        raise RuntimeError("Safe model loading requires skops. Install the project dependency: pip install skops.") from exc
    required = set(sio.get_untrusted_types(data=payload))
    approved = set(trusted_types or [])
    if not required.issubset(approved):
        raise ValueError("Model contains untrusted Python types. Review the type list and explicitly approve it before loading.")
    return sio.loads(payload, trusted=sorted(approved))


def register_model_artifact(*, payload: bytes, model_name: str, model_family: str,
        task_type: str, outcome: str, features: list[str], user_scope: str,
        project_scope: str, species_scope: str = "unspecified", group_column: str | None = None,
        dataset_fingerprint: str | None = None, training_records: int = 0,
        training_groups: int = 0, random_seed: int | None = None,
        validation_metrics: dict | None = None, notes: str = "", status: str = "candidate") -> dict:
    """Register a model binary as a new immutable version."""
    if not isinstance(payload, (bytes, bytearray)) or not payload:
        raise ValueError("A non-empty serialized model artifact is required.")
    if task_type not in {"regression", "classification"}:
        raise ValueError("task_type must be regression or classification.")
    if status not in {"candidate", "approved"}:
        raise ValueError("New model versions must be candidate or approved.")
    if not features or len(set(features)) != len(features):
        raise ValueError("Provide a non-empty list of unique predictors.")
    if int(training_records) < 1 or int(training_groups) < 1:
        raise ValueError("Training record and group counts must be positive.")

    model_id = str(uuid.uuid4())
    name = _safe_name(model_name)
    stamp = datetime.now(timezone.utc).isoformat()
    digest = hashlib.sha256(payload).hexdigest()
    # Each registration starts a model lineage; explicit new versions use add_model_version.
    model_dir = _artifact_root() / model_id
    model_dir.mkdir(parents=True, exist_ok=False)
    artifact = model_dir / "v1.skops"
    temp = model_dir / ".v1.tmp"
    temp.write_bytes(bytes(payload))
    os.replace(temp, artifact)
    with closing(_connect()) as con:
        con.execute("""INSERT INTO registered_models VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (model_id, 1, str(user_scope), str(project_scope), str(species_scope), name,
             str(model_family), task_type, str(outcome), json.dumps(list(features)),
             str(group_column) if group_column else None, dataset_fingerprint,
             int(training_records), int(training_groups), random_seed,
             json.dumps(validation_metrics or {}, sort_keys=True, default=str), str(notes), status,
             str(artifact.resolve()), digest, stamp, stamp if status == "approved" else None))
        con.commit()
    return {"model_id": model_id, "version": 1, "model_name": name, "status": status,
            "artifact_sha256": digest, "created_at": stamp}


def add_model_version(model_id: str, *, payload: bytes, user_scope: str,
                       validation_metrics: dict | None = None, notes: str = "",
                       status: str = "candidate", training_records: int | None = None,
                       training_groups: int | None = None, dataset_fingerprint: str | None = None) -> dict:
    if not payload:
        raise ValueError("A non-empty serialized model artifact is required.")
    if status not in {"candidate", "approved"}:
        raise ValueError("New model versions must be candidate or approved.")
    with closing(_connect()) as con:
        previous = con.execute("SELECT * FROM registered_models WHERE model_id=? AND user_scope=? ORDER BY version DESC LIMIT 1",
                               (str(model_id), str(user_scope))).fetchone()
        if previous is None:
            raise KeyError("Model was not found in the current user scope.")
        version = int(previous["version"]) + 1
        stamp = datetime.now(timezone.utc).isoformat()
        digest = hashlib.sha256(payload).hexdigest()
        artifact = _artifact_root() / str(model_id) / f"v{version}.skops"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        temp = artifact.with_suffix(".tmp")
        temp.write_bytes(bytes(payload)); os.replace(temp, artifact)
        con.execute("""INSERT INTO registered_models VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (previous["model_id"], version, previous["user_scope"], previous["project_scope"],
             previous["species_scope"], previous["model_name"], previous["model_family"],
             previous["task_type"], previous["outcome"], previous["features_json"],
             previous["group_column"], dataset_fingerprint or previous["dataset_fingerprint"],
             int(training_records if training_records is not None else previous["training_records"]),
             int(training_groups if training_groups is not None else previous["training_groups"]),
             previous["random_seed"], json.dumps(validation_metrics or {}, sort_keys=True, default=str),
             str(notes), status, str(artifact.resolve()), digest, stamp, stamp if status == "approved" else None))
        con.commit()
    return {"model_id": str(model_id), "version": version, "status": status,
            "artifact_sha256": digest, "created_at": stamp}


def list_models(user_scope: str, project_scope: str | None = None, include_all_projects: bool = False) -> list[dict]:
    clauses = ["user_scope=?"]; params: list = [str(user_scope)]
    if project_scope is not None and not include_all_projects:
        clauses.append("project_scope=?"); params.append(str(project_scope))
    with closing(_connect()) as con:
        rows = con.execute("SELECT * FROM registered_models WHERE " + " AND ".join(clauses) +
                           " ORDER BY model_name, version DESC", params).fetchall()
    return [_row_dict(row, include_path=False) for row in rows]


def get_model(model_id: str, version: int, user_scope: str) -> dict | None:
    with closing(_connect()) as con:
        row = con.execute("SELECT * FROM registered_models WHERE model_id=? AND version=? AND user_scope=?",
                          (str(model_id), int(version), str(user_scope))).fetchone()
    return _row_dict(row, include_path=True) if row else None


def _row_dict(row, include_path=False):
    d = dict(row)
    d["features"] = json.loads(d.pop("features_json"))
    d["validation_metrics"] = json.loads(d.pop("validation_metrics_json"))
    if not include_path:
        d.pop("artifact_path", None)
    return d


def set_model_status(model_id: str, version: int, user_scope: str, status: str) -> None:
    if status not in {"candidate", "approved", "retired"}:
        raise ValueError("Invalid model lifecycle status.")
    with closing(_connect()) as con:
        cur = con.execute("UPDATE registered_models SET status=?, approved_at=? WHERE model_id=? AND version=? AND user_scope=?",
                          (status, datetime.now(timezone.utc).isoformat() if status == "approved" else None,
                           str(model_id), int(version), str(user_scope)))
        con.commit()
    if cur.rowcount != 1:
        raise KeyError("Model version was not found in the current user scope.")


def read_model_artifact(model_id: str, version: int, user_scope: str) -> tuple[dict, bytes]:
    record = get_model(model_id, version, user_scope)
    if record is None:
        raise KeyError("Model version was not found in the current user scope.")
    path = Path(record["artifact_path"]).resolve()
    root = _artifact_root().resolve()
    if root not in path.parents or not path.is_file():
        raise FileNotFoundError("Registered model artifact is missing or outside the registry directory.")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != record["artifact_sha256"]:
        raise ValueError("Model artifact checksum mismatch. The artifact may have been modified.")
    return record, payload


def load_registered_model(model_id: str, version: int, user_scope: str, trusted_types=None):
    record, payload = read_model_artifact(model_id, version, user_scope)
    model = deserialize_estimator(payload, trusted_types=trusted_types)
    return record, model
