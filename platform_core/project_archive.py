"""Portable, integrity-checked project archive import/export."""
from __future__ import annotations
import hashlib, io, json, zipfile, uuid
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
    from platform_core.storage import get_project, list_datasets, load_dataset
    project = get_project(tenant_id, project_id, subject)
    datasets = list_datasets(tenant_id, project_id, subject)
    manifest = {
        "format": ARCHIVE_FORMAT, "archive_version": ARCHIVE_VERSION,
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "project": {k: project.get(k) for k in ("name", "species", "description")},
        "datasets": [], "analysis_runs": [], "research_state": {"settings": [], "experiments": []}
    }
    if include_research_state:
        from analysis_engine.experiment_registry import export_project_state
        manifest["research_state"] = export_project_state(subject, project_id, tenant_id=tenant_id)
        # Backward compatibility for projects whose settings were scoped by project name.
        if not manifest["research_state"].get("settings") and not manifest["research_state"].get("experiments"):
            from platform_core.storage import backend_name
            if backend_name() == "local":
                legacy_state = export_project_state(subject, project.get("name", ""))
                if legacy_state.get("settings") or legacy_state.get("experiments"):
                    manifest["research_state"] = legacy_state
    if include_research_state:
        from platform_core.run_registry import list_runs, load_run_artifact
        runs = list_runs(1000, tenant_id=tenant_id, project_id=project_id, user_subject=subject)
        for run in runs:
            item = {k: run.get(k) for k in ("run_id", "created_utc", "dataset_name", "dataset_fingerprint", "outcome", "species", "status", "dataset_id", "module_key", "manifest_json", "summary_json")}
            if run.get("artifact_available"):
                member = f"analysis_runs/{run['run_id']}/artifact.zip"
                item["artifact_path"] = member
                item["artifact_sha256"] = _sha(load_run_artifact(run["run_id"], tenant_id=tenant_id, project_id=project_id, user_subject=subject))
            manifest["analysis_runs"].append(item)
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
        for run in manifest.get("analysis_runs", []):
            if run.get("artifact_path"):
                artifact = load_run_artifact(run["run_id"], tenant_id=tenant_id, project_id=project_id, user_subject=subject)
                if _sha(artifact) != run.get("artifact_sha256"):
                    raise IOError(f"Analysis artifact integrity check failed for run {run['run_id']}.")
                zf.writestr(run["artifact_path"], artifact)
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, default=str, sort_keys=True))
    payload = output.getvalue()
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise ValueError("Project archive exceeds the 200 MB export limit. Export fewer datasets or analysis runs.")
    return payload


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
        runs = manifest.get("analysis_runs", [])
        if not isinstance(runs, list):
            raise ValueError("Analysis-run archive manifest must be a list.")
        for run in runs:
            artifact_path = run.get("artifact_path")
            if artifact_path:
                if artifact_path not in names or not artifact_path.startswith("analysis_runs/") or not artifact_path.endswith("/artifact.zip"):
                    raise ValueError("Analysis-run artifact path is missing or invalid.")
                artifact = zf.read(artifact_path)
                if _sha(artifact) != run.get("artifact_sha256"):
                    raise ValueError(f"Analysis-run artifact checksum validation failed: {artifact_path}")
                from analysis_engine.run_artifacts import read_run_artifact
                read_run_artifact(artifact)
        return manifest


def import_project_archive(payload: bytes, tenant_id: str, subject: str, project_name: str | None = None, restore_research_state: bool = True) -> dict:
    from platform_core.storage import create_project, save_dataset
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
                imported.append({"dataset_id": result["id"], "source_dataset_id": entry.get("source_dataset_id"), "name": entry.get("original_filename"), "rows": len(df)})
    except Exception as exc:
        raise RuntimeError(f"Project {project_id} was created, but import did not complete. It has been retained for audit and recovery; inspect its imported datasets before retrying. Cause: {exc}") from exc
    if restore_research_state:
        from analysis_engine.experiment_registry import import_project_state
        import_project_state(subject, project_id, manifest.get("research_state") or {}, tenant_id=tenant_id)
        from platform_core.run_registry import save_run, save_run_artifact
        from analysis_engine.run_artifacts import read_run_artifact, build_run_artifact
        dataset_id_map = {str(x.get("source_dataset_id")): x["dataset_id"] for x in imported if x.get("source_dataset_id")}
        imported_runs = []
        try:
            with zipfile.ZipFile(io.BytesIO(payload), "r") as zf:
                for item in manifest.get("analysis_runs", []):
                    new_run_id = str(uuid.uuid4())
                    run_manifest = json.loads(item.get("manifest_json") or "{}")
                    run_summary = json.loads(item.get("summary_json") or "{}")
                    run_manifest["imported_from_run_id"] = item.get("run_id")
                    run_manifest["run_id"] = new_run_id
                    run_manifest["project_id"] = project_id
                    old_dataset_id = item.get("dataset_id")
                    new_dataset_id = dataset_id_map.get(str(old_dataset_id)) if old_dataset_id else None
                    run_manifest["dataset_id"] = new_dataset_id
                    save_run(new_run_id, run_manifest, run_summary, status=item.get("status") or "completed",
                        tenant_id=tenant_id, project_id=project_id, dataset_id=new_dataset_id,
                        user_subject=subject, module_key=item.get("module_key") or "integrated_analysis")
                    if item.get("artifact_path"):
                        restored = read_run_artifact(zf.read(item["artifact_path"]))
                        restored["manifest"].update(run_manifest)
                        rebuilt = build_run_artifact(restored, dataset=restored.get("dataset"), figure_html=restored.get("figure_html"))
                        save_run_artifact(new_run_id, rebuilt, tenant_id=tenant_id, project_id=project_id, user_subject=subject)
                    imported_runs.append({"run_id": new_run_id, "source_run_id": item.get("run_id"), "artifact_restored": bool(item.get("artifact_path"))})
        except Exception as exc:
            raise RuntimeError(f"Project {project_id} datasets were imported, but analysis-run restoration did not complete. Inspect the new project before retrying. Cause: {exc}") from exc
    else:
        imported_runs = []
    return {"project_id": project_id, "project_name": name, "datasets_imported": len(imported), "datasets": imported, "analysis_runs_imported": len(imported_runs), "analysis_runs": imported_runs, "research_state_restored": bool(restore_research_state)}
