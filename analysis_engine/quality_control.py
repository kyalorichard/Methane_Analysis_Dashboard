"""Unified, non-destructive dataset and phenotype quality-control engine.

QC flags are screening evidence, not automatic exclusion or proof of invalidity.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json
import numpy as np
import pandas as pd

ENGINE_VERSION = "1.0.0"


def dataframe_fingerprint(df: pd.DataFrame) -> str:
    """Stable best-effort fingerprint of values, index and column metadata."""
    h = hashlib.sha256()
    h.update(json.dumps([str(c) for c in df.columns], ensure_ascii=False).encode())
    h.update(json.dumps([str(x) for x in df.dtypes]).encode())
    try:
        h.update(pd.util.hash_pandas_object(df, index=True).values.tobytes())
    except Exception:
        h.update(df.to_csv(index=True).encode("utf-8", errors="replace"))
    return h.hexdigest()


def run_quality_control(df: pd.DataFrame, *, rules: dict | None = None,
                        animal_id: str | None = None, time_col: str | None = None,
                        outlier_method: str = "IQR", iqr_multiplier: float = 1.5) -> dict:
    """Run structural, missingness, numeric, outlier and repeated-measure checks."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("QC expects a pandas DataFrame.")
    rules = rules or {}
    findings = []
    def add(check, severity, variable="", count=0, detail="", recommendation=""):
        findings.append({"check": check, "severity": severity, "variable": str(variable),
                         "n_flagged": int(count), "detail": detail,
                         "recommendation": recommendation})

    if df.empty: add("Dataset is empty", "critical", count=0, detail="No records are available.", recommendation="Import a non-empty dataset.")
    if len(df.columns) == 0: add("No variables", "critical", detail="Dataset has no columns.")
    if df.columns.duplicated().any(): add("Duplicate column names", "critical", count=int(df.columns.duplicated().sum()), recommendation="Rename columns uniquely before analysis.")
    blank_cols = [str(c) for c in df.columns if not str(c).strip()]
    if blank_cols: add("Blank column names", "warning", count=len(blank_cols), detail=", ".join(blank_cols), recommendation="Assign explicit variable names.")
    dup = int(df.duplicated().sum())
    if dup: add("Exact duplicate rows", "warning", count=dup, detail=f"{dup} rows duplicate an earlier row.", recommendation="Review duplicates; do not remove automatically.")
    empty_rows = int(df.isna().all(axis=1).sum())
    if empty_rows: add("Fully empty rows", "warning", count=empty_rows, recommendation="Review whether empty rows should be excluded from an analysis copy.")

    miss = df.isna().sum()
    for col, n in miss[miss > 0].items():
        pct = float(n / max(len(df), 1) * 100)
        sev = "warning" if pct < 50 else "high"
        add("Missingness", sev, col, int(n), f"{pct:.1f}% missing ({int(n)}/{len(df)} records).", "Investigate missingness mechanism and report analysis-specific handling.")

    numeric = df.select_dtypes(include=[np.number]).columns
    for col in numeric:
        s = pd.to_numeric(df[col], errors="coerce")
        nonfinite = int((~np.isfinite(s.dropna())).sum())
        if nonfinite: add("Non-finite numeric values", "high", col, nonfinite, "Infinite values detected.", "Resolve or explicitly handle non-finite measurements.")
        valid = s[np.isfinite(s)]
        if len(valid) and valid.nunique(dropna=True) <= 1:
            add("Constant numeric variable", "info", col, len(valid), "No observed variation.", "Confirm whether this variable is intentionally constant.")
        if len(valid) >= 4:
            q1, q3 = valid.quantile([.25, .75]); spread = q3-q1
            if spread > 0:
                mult = float(iqr_multiplier)
                out = (valid < q1-mult*spread) | (valid > q3+mult*spread)
                if out.any():
                    add(f"Potential outliers ({outlier_method})", "warning", col, int(out.sum()),
                        f"{int(out.sum())} values outside {mult:g}×IQR fences.",
                        "Inspect source records, units and biological plausibility; retain unless justified otherwise.")

    for col, rule in rules.items():
        if col not in df.columns or not isinstance(rule, dict): continue
        vals = pd.to_numeric(df[col], errors="coerce")
        bad = pd.Series(False, index=df.index)
        if rule.get("min") is not None: bad |= vals < float(rule["min"])
        if rule.get("max") is not None: bad |= vals > float(rule["max"])
        n = int(bad.fillna(False).sum())
        if n:
            add("Configured study-specific range", "high", col, n,
                f"{n} values outside [{rule.get('min', '-∞')}, {rule.get('max', '∞')}]. Rationale: {rule.get('source','Not supplied')}.",
                "Verify units and protocol limits; decide whether to retain, correct or exclude with documented justification.")

    repeated = {}
    if animal_id and animal_id in df.columns:
        ids = df[animal_id]
        missing_ids = int(ids.isna().sum())
        if missing_ids: add("Missing animal identifiers", "high", animal_id, missing_ids, "Records cannot be assigned to an animal.", "Resolve identifiers before animal-level or repeated-measures analysis.")
        counts = ids.dropna().value_counts()
        repeated = {"n_animals": int(counts.size), "single_record_animals": int((counts == 1).sum()),
                    "repeated_animals": int((counts > 1).sum()), "max_records_per_animal": int(counts.max()) if len(counts) else 0}
        if len(counts) and (counts == 1).any():
            add("Single-record animals", "info", animal_id, int((counts == 1).sum()), "Animals with one record cannot contribute within-animal repeatability information.", "Check the intended repeated-measures design.")
        if time_col and time_col in df.columns:
            tmp = df[[animal_id, time_col]].dropna().copy()
            dup_time = int(tmp.duplicated([animal_id, time_col]).sum())
            if dup_time: add("Duplicate animal-time combinations", "warning", f"{animal_id} / {time_col}", dup_time, "Multiple records share the same animal and time key.", "Check replicate structure and whether an additional replicate identifier is required.")

    severity_counts = {s: sum(x["severity"] == s for x in findings) for s in ("critical", "high", "warning", "info")}
    blocking = severity_counts["critical"] > 0
    score = max(0, 100 - 25*severity_counts["critical"] - 12*severity_counts["high"] - 5*severity_counts["warning"] - severity_counts["info"])
    return {"engine_version": ENGINE_VERSION, "created_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_fingerprint": dataframe_fingerprint(df), "n_records": int(len(df)),
            "n_variables": int(df.shape[1]), "missing_cells": int(df.isna().sum().sum()),
            "duplicate_rows": dup, "findings": findings, "severity_counts": severity_counts,
            "quality_screening_score": int(score), "blocking_issues": bool(blocking),
            "animal_repeated_measure_summary": repeated,
            "rules": rules, "settings": {"outlier_method": outlier_method, "iqr_multiplier": float(iqr_multiplier), "animal_id": animal_id, "time_col": time_col},
            "interpretation": "Screening score is a prioritisation aid, not a validated measure of scientific data quality. Flags require investigator review; no records were changed or removed."}


def findings_frame(report: dict) -> pd.DataFrame:
    return pd.DataFrame(report.get("findings", []), columns=["check", "severity", "variable", "n_flagged", "detail", "recommendation"])
