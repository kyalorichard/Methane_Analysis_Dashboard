"""Portable, integrity-checked project archive import/export."""
from __future__ import annotations
import hashlib, io, json, zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath

ARCHIVE_FORMAT = "methane-phenotype-project"
ARCHIVE_VERSION = 1
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024
MAX_MEMBER_BYTES = 200 * 1024 * 1024
ALLOWED_SPECIES = {"sheep", "goat", "cattle", "buffalo", "camel", "other"}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_project_archive(tenant_id: str, subject: str, project_id: str, include_research_state: bool = True) -> bytes:
    from platform_core.workspace import get_project, list_datasets, load_dataset
    project = get_project(tenant_id, project_id, subject)
    datasets = list_datasets(tenant_id, project_id, subject)
    manifest = {
        "format": ARCHIVE_FORMAT, "archive_version": ARCHIVE_VERSION,
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "project": {k: project.get(k) for k in ("name", "species", "description")},
        "datasets": [], "research_state": {"settings": [], "experiments": []}
    }
    if include_research_state:
        from analysis_engine.experiment_registry import export_project_state
        manifest["research_state"] = export_project_state(subject, project.get("name", ""))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for i, item in enumerate(datasets, start=1):
            df, filename, species = load_dataset(tenant_id, project_id, item["id"], subject)
            # Canonical data payload is portable Parquet; never export tenant-specific S3 keys.
            from analysis_engine.io import dataframe_to_parquet_bytes
            payload = dataframe_to_parquet_bytes(df)
            member = f"datasets/{i:04d}.parquet"
            protocol = item.get("protocol_json") or {}
            metadata = {
                "original_filename": filename, "species": species,
                "row_count": int(len(df)), "column_count": int(len(df.columns)),
                "sha256": _sha(payload), "protocol": protocol,
                "source_format": item.get("source_format") or item.get("file_format") or "unknown",
                "source_dataset_id": item["id"]
            }
            manifest["datasets"].append({"path": member, **metadata})
            zf.writestr(member, payload)
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, default=str, sort_keys=True))
    return output.getvalue()


def inspect_project_archive(payload: bytes) -> dict:
    if not payload or len(payload) > MAX_ARCHIVE_BYTES:
        raise ValueError("Project archive is empty or exceeds the 200 MB upload limit.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(payload), "r")
    except zipfile.BadZipFile as exc:
        raise ValueError("The selected file is not a valid ZIP project archive.") from exc
    with zf:
        infos = zf.infolist()
        names = [x.filename for x in infos]
        if len(names) != len(set(names)):
            raise ValueError("Archive contains duplicate member paths.")
        total = 0
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
                raise ValueError("Archive contains an unsafe file path.")
            if info.file_size > MAX_MEMBER_BYTES:
                raise ValueError(f"Archive member exceeds the 200 MB limit: {info.filename}")
            total += info.file_size
        if total > MAX_ARCHIVE_BYTES:
            raise ValueError("Uncompressed project archive exceeds the 200 MB limit.")
        if "manifest.json" not in names:
            raise ValueError("Project archive is missing manifest.json.")
        try:
            manifest = json.loads(zf.read("manifest.json"))
        except Exception as exc:
            raise ValueError("Project manifest is not valid JSON.") from exc
        if manifest.get("format") != ARCHIVE_FORMAT or manifest.get("archive_version") != ARCHIVE_VERSION:
            raise ValueError("Unsupported project archive format or version.")
        project = manifest.get("project") or {}
        if not str(project.get("name", "")).strip() or project.get("species") not in ALLOWED_SPECIES:
            raise ValueError("Project metadata is incomplete or has an unsupported species.")
        entries = manifest.get("datasets")
        if not isinstance(entries, list):
            raise ValueError("Project dataset manifest must be a list.")
        for entry in entries:
            member = entry.get("path", "")
            if member not in names or not member.startswith("datasets/") or not member.endswith(".parquet"):
                raise ValueError("Dataset path is missing or not a supported canonical Parquet member.")
            data = zf.read(member)
            if _sha(data) != entry.get("sha256"):
                raise ValueError(f"Dataset integrity check failed: {member}")
            if entry.get("species") != project["species"]:
                raise ValueError(f"Dataset species does not match the project species in {member}.")
        return manifest


def import_project_archive(payload: bytes, tenant_id: str, subject: str, project_name: str | None = None, restore_research_state: bool = True) -> dict:
    from platform_core.workspace import create_project, save_dataset
    manifest = inspect_project_archive(payload)
    source = manifest["project"]
    name = (project_name or source["name"]).strip()
    if not name:
        raise ValueError("A destination project name is required.")
    project_id = create_project(tenant_id, subject, name, source["species"], source.get("description") or "Imported from a portable project archive.")
    imported = []
    try:
        with zipfile.ZipFile(io.BytesIO(payload), "r") as zf:
            for entry in manifest["datasets"]:
                data = zf.read(entry["path"])
                frame = io.BytesIO(data)
                import pandas as pd
                df = pd.read_parquet(frame, engine="pyarrow")
                if len(df) != int(entry.get("row_count", -1)) or len(df.columns) != int(entry.get("column_count", -1)):
                    raise ValueError(f"Dataset dimensions do not match the manifest: {entry['path']}")
                result = save_dataset(
                    tenant_id, subject, project_id,
                    entry.get("original_filename") or entry["path"].split("/")[-1],
                    data, df, entry["species"], entry.get("protocol") or {}
                )
                imported.append({"dataset_id": result["id"], "name": entry.get("original_filename"), "rows": len(df)})
    except Exception as exc:
        raise RuntimeError(f"Project {project_id} was created, but import did not complete. It has been retained for audit and recovery; inspect its imported datasets before retrying. Cause: {exc}") from exc
    if restore_research_state:
        from analysis_engine.experiment_registry import import_project_state
        import_project_state(subject, name, manifest.get("research_state") or {})
    return {"project_id": project_id, "project_name": name, "datasets_imported": len(imported), "datasets": imported, "research_state_restored": bool(restore_research_state)}
