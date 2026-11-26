"""Safe, portable serialization for reproducible analysis-run outputs.

Only JSON, CSV and HTML are stored; no pickle or executable model objects.
"""
from __future__ import annotations
import io, json, zipfile
from pathlib import PurePosixPath
import pandas as pd

ARTIFACT_FORMAT = "methane-analysis-run-artifact"
ARTIFACT_VERSION = 1
MAX_ARTIFACT_BYTES = 100 * 1024 * 1024


def build_run_artifact(result: dict, *, dataset: pd.DataFrame | None = None, figure_html: str | None = None) -> bytes:
    manifest = result.get("manifest") or {}
    summary = result.get("summary") or {}
    tables = result.get("tables") or {}
    files: dict[str, bytes] = {
        "artifact_manifest.json": json.dumps({"format": ARTIFACT_FORMAT, "version": ARTIFACT_VERSION,
            "run_id": manifest.get("run_id"), "dataset_fingerprint_sha256": manifest.get("dataset_fingerprint_sha256"),
            "dataset_id": manifest.get("dataset_id"), "module_key": "integrated_analysis",
            "dataset_format": None}, indent=2, default=str).encode(),
        "manifest.json": json.dumps(manifest, indent=2, default=str).encode(),
        "summary.json": json.dumps(summary, indent=2, default=str).encode(),
    }
    for name, frame in tables.items():
        if isinstance(frame, pd.DataFrame):
            safe_name = "".join(c for c in str(name) if c.isalnum() or c in "_- ").strip().replace(" ", "_")[:80] or "table"
            files[f"tables/{safe_name}.csv"] = frame.to_csv(index=False).encode("utf-8")
    if dataset is not None:
        # Store the exact analysis input with the outputs so reopening does not
        # depend on a mutable session or a still-active browser dataset.
        try:
            from analysis_engine.io import dataframe_to_parquet_bytes
            files["data/analysis_dataset.parquet"] = dataframe_to_parquet_bytes(dataset, compression="snappy")
            dataset_format = "parquet"
        except Exception:
            files["data/analysis_dataset.csv"] = dataset.to_csv(index=False).encode("utf-8")
            dataset_format = "csv"
        meta = json.loads(files["artifact_manifest.json"])
        meta["dataset_format"] = dataset_format
        meta["dataset_columns"] = [str(c) for c in dataset.columns]
        meta["dataset_dtypes"] = {str(c): str(t) for c, t in dataset.dtypes.items()}
        files["artifact_manifest.json"] = json.dumps(meta, indent=2, default=str).encode()
    if figure_html:
        files["figures/phenotype_distribution.html"] = figure_html.encode("utf-8")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for name, payload in files.items():
            zf.writestr(name, payload)
    payload = out.getvalue()
    if len(payload) > MAX_ARTIFACT_BYTES:
        raise ValueError("Analysis artifacts exceed the 100 MB persistence limit. Download the full report package instead.")
    return payload


def read_run_artifact(payload: bytes) -> dict:
    if not payload or len(payload) > MAX_ARTIFACT_BYTES:
        raise ValueError("Analysis artifact is empty or exceeds the 100 MB limit.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(payload), "r")
    except zipfile.BadZipFile as exc:
        raise ValueError("Stored analysis artifact is not a valid ZIP file.") from exc
    with zf:
        names = zf.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Analysis artifact contains duplicate member names.")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise ValueError("Analysis artifact contains an unsafe member path.")
        required = {"artifact_manifest.json", "manifest.json", "summary.json"}
        if not required.issubset(names):
            raise ValueError("Analysis artifact is missing required provenance files.")
        metadata = json.loads(zf.read("artifact_manifest.json"))
        if metadata.get("format") != ARTIFACT_FORMAT or metadata.get("version") != ARTIFACT_VERSION:
            raise ValueError("Unsupported analysis artifact format or version.")
        tables = {}
        for name in names:
            if name.startswith("tables/") and name.endswith(".csv"):
                key = PurePosixPath(name).stem
                tables[key] = pd.read_csv(io.BytesIO(zf.read(name)))
        figure = zf.read("figures/phenotype_distribution.html").decode("utf-8") if "figures/phenotype_distribution.html" in names else None
        dataset = None
        if "data/analysis_dataset.parquet" in names:
            dataset = pd.read_parquet(io.BytesIO(zf.read("data/analysis_dataset.parquet")), engine="pyarrow")
        elif "data/analysis_dataset.csv" in names:
            dataset = pd.read_csv(io.BytesIO(zf.read("data/analysis_dataset.csv")))
        return {"dataset": dataset, "manifest": json.loads(zf.read("manifest.json")),
                "summary": json.loads(zf.read("summary.json")), "tables": tables,
                "figure_html": figure, "artifact_manifest": metadata}
