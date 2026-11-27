"""Unified, non-destructive dataset and phenotype quality-control engine.

QC flags are screening evidence, not automatic exclusion or proof of invalidity.
"""
from __future__ import annotations
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from analysis_engine.data_provenance import dataframe_fingerprint

ENGINE_VERSION = "1.1.0"


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


def flag_data_quality_rows(df: pd.DataFrame, columns: list[str] | None = None,
                           duration_col: str | None = None, min_duration: float | None = None,
                           nonnegative_columns: list[str] | None = None,
                           max_missing_pct: float = 30.0) -> pd.DataFrame:
    """Create a non-destructive row-level QC review queue.

    Outliers are screening flags only. The function never drops or edits records.
    ``max_missing_pct`` is retained for API compatibility and future variable-level
    summaries; row-level flags are emitted for missing observations regardless.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Row-level QC expects a pandas DataFrame.")
    selected = list(dict.fromkeys(columns or df.select_dtypes(include="number").columns.tolist()))
    nonnegative = set(nonnegative_columns or [])
    rows = []
    for col in selected:
        if col not in df.columns:
            continue
        x = pd.to_numeric(df[col], errors="coerce")
        valid = x.replace([np.inf, -np.inf], np.nan).dropna()
        if valid.empty:
            continue
        q1, q3 = valid.quantile([.25, .75]); spread = q3 - q1
        lo, hi = (q1 - 1.5 * spread, q3 + 1.5 * spread) if spread > 0 else (valid.min(), valid.max())
        for pos, (idx, value) in enumerate(x.items()):
            flags = []
            if pd.isna(value) or not np.isfinite(value):
                flags.append("Missing or non-finite value")
            else:
                if col in nonnegative and value < 0:
                    flags.append("Negative value in variable configured as non-negative")
                if value < lo or value > hi:
                    flags.append("IQR outlier (review; not automatic exclusion)")
            if duration_col and duration_col in df.columns and min_duration is not None:
                duration = pd.to_numeric(pd.Series([df.iloc[pos][duration_col]]), errors="coerce").iloc[0]
                if pd.isna(duration):
                    flags.append("Missing recording duration")
                elif duration < min_duration:
                    flags.append("Below minimum recording duration")
            if flags:
                rows.append({"row_index": idx, "row_position": pos, "variable": col,
                             "value": value, "flags": "; ".join(flags)})
    return pd.DataFrame(rows, columns=["row_index", "row_position", "variable", "value", "flags"])


def configured_range_summary(df: pd.DataFrame, rules: dict | None = None) -> pd.DataFrame:
    """Summarise configured numeric range violations using the canonical masks."""
    records = []
    for col, rule in (rules or {}).items():
        if col not in df.columns or not isinstance(rule, dict):
            continue
        x = pd.to_numeric(df[col], errors="coerce")
        below = int((x < float(rule["min"])).fillna(False).sum()) if rule.get("min") is not None else 0
        above = int((x > float(rule["max"])).fillna(False).sum()) if rule.get("max") is not None else 0
        records.append({"variable": col, "minimum_rule": rule.get("min"),
                        "maximum_rule": rule.get("max"), "below_min_n": below,
                        "above_max_n": above, "missing_n": int(x.isna().sum()),
                        "flagged_n": below + above,
                        "rule_source": rule.get("source", "user-configured; not a validated biological threshold"),
                        "status": "REVIEW" if below + above else "PASS"})
    return pd.DataFrame(records, columns=["variable", "minimum_rule", "maximum_rule",
        "below_min_n", "above_max_n", "missing_n", "flagged_n", "rule_source", "status"])


def findings_frame(report: dict) -> pd.DataFrame:
    return pd.DataFrame(report.get("findings", []), columns=["check", "severity", "variable", "n_flagged", "detail", "recommendation"])


def configured_range_mask(df: pd.DataFrame, variable: str, rule: dict) -> pd.Series:
    """Return a boolean mask for finite numeric values outside a configured range."""
    if variable not in df.columns:
        raise KeyError(f"Variable {variable!r} is not present in the dataset.")
    values = pd.to_numeric(df[variable], errors="coerce")
    mask = pd.Series(False, index=df.index)
    if rule.get("min") is not None:
        mask |= values < float(rule["min"])
    if rule.get("max") is not None:
        mask |= values > float(rule["max"])
    return mask.fillna(False)


def apply_range_disposition(
    df: pd.DataFrame,
    *,
    variable: str,
    row_positions: list[int],
    action: str,
    method: str | None = None,
    group_col: str | None = None,
    animal_id: str | None = None,
    time_col: str | None = None,
    valid_mask: pd.Series | None = None,
    lower_quantile: float = 0.05,
    upper_quantile: float = 0.95,
) -> tuple[pd.DataFrame, dict]:
    """Apply an explicit range decision to a copy; never mutate the source frame.

    row_positions are zero-based positional row identifiers from the currently
    active source snapshot. Estimation donors are restricted to values that pass
    the configured range when valid_mask is supplied.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("QC disposition expects a pandas DataFrame.")
    if variable not in df.columns:
        raise KeyError(f"Variable {variable!r} is not present in the dataset.")
    positions = sorted(set(int(p) for p in row_positions))
    if not positions or any(p < 0 or p >= len(df) for p in positions):
        raise ValueError("Select at least one valid flagged row.")
    action_key = str(action).strip().lower()
    if action_key not in {"keep", "drop", "estimate", "winsorize"}:
        raise ValueError("Action must be 'keep', 'drop', 'estimate' or 'winsorize'.")

    result = df.copy(deep=True)
    original = pd.to_numeric(df[variable], errors="coerce").iloc[positions]
    audit = {
        "action": action_key,
        "variable": str(variable),
        "row_positions": positions,
        "original_values": [None if pd.isna(v) else float(v) for v in original.tolist()],
        "replacement_values": [],
        "method": method,
        "group_col": group_col,
        "animal_id": animal_id,
        "time_col": time_col,
        "lower_quantile": float(lower_quantile) if action_key == "winsorize" else None,
        "upper_quantile": float(upper_quantile) if action_key == "winsorize" else None,
        "records_before": int(len(df)),
        "records_after": int(len(df)),
    }
    if action_key == "keep":
        audit["replacement_values"] = audit["original_values"]
        return result, audit

    if action_key == "drop":
        keep = np.ones(len(df), dtype=bool)
        keep[positions] = False
        result = df.iloc[keep].copy()
        audit["records_after"] = int(len(result))
        return result, audit

    values = pd.to_numeric(df[variable], errors="coerce").astype(float).copy()
    if action_key == "winsorize":
        if not (0.0 <= float(lower_quantile) < float(upper_quantile) <= 1.0):
            raise ValueError("Winsorization quantiles must satisfy 0 ≤ lower < upper ≤ 1.")
        donor = values.notna() & np.isfinite(values)
        if valid_mask is not None:
            donor &= valid_mask.reindex(df.index, fill_value=False).astype(bool)
        donor.iloc[positions] = False
        pool = values[donor]
        if len(pool) < 2:
            raise ValueError("At least two valid, unselected observations are required for winsorization.")
        lower_bound = float(pool.quantile(float(lower_quantile)))
        upper_bound = float(pool.quantile(float(upper_quantile)))
        if not np.isfinite(lower_bound) or not np.isfinite(upper_bound) or lower_bound > upper_bound:
            raise ValueError("Could not derive valid winsorization thresholds from the donor observations.")
        replacements = values.iloc[positions].clip(lower=lower_bound, upper=upper_bound).astype(float)
        result[variable] = values.astype(float)
        for pos, replacement in zip(positions, replacements.tolist()):
            result.iat[pos, result.columns.get_loc(variable)] = float(replacement)
        audit.update({
            "method": "Quantile winsorization",
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "replacement_values": [float(x) for x in replacements.tolist()],
            "records_after": int(len(result)),
        })
        return result, audit

    donor = values.notna() & np.isfinite(values)
    if valid_mask is not None:
        donor &= valid_mask.reindex(df.index, fill_value=False).astype(bool)
    target_mask = np.zeros(len(df), dtype=bool)
    target_mask[positions] = True
    # Never use the flagged observations as donors for their own estimates.
    donor.iloc[positions] = False
    estimates = pd.Series(np.nan, index=df.index, dtype=float)

    if method == "Global median":
        pool = values[donor]
        if pool.empty:
            raise ValueError("No in-range observations are available to estimate from.")
        estimates.iloc[positions] = float(pool.median())
    elif method == "Group median":
        if not group_col or group_col not in df.columns:
            raise ValueError("Select a valid grouping variable for group-median estimation.")
        donors = pd.DataFrame({"group": df[group_col], "value": values.where(donor)})
        medians = donors.groupby("group", dropna=False)["value"].median()
        for pos in positions:
            key = df[group_col].iloc[pos]
            estimate = medians.get(key, np.nan)
            if pd.notna(estimate):
                estimates.iloc[pos] = float(estimate)
    elif method == "Within-animal interpolation":
        if not animal_id or animal_id not in df.columns or not time_col or time_col not in df.columns:
            raise ValueError("Within-animal interpolation requires valid animal and time variables.")
        time_values = df[time_col]
        if pd.api.types.is_datetime64_any_dtype(time_values):
            numeric_time = pd.to_datetime(time_values, errors="coerce").map(lambda x: x.timestamp() if pd.notna(x) else np.nan)
        else:
            numeric_time = pd.to_numeric(time_values, errors="coerce")
        work = pd.DataFrame({"animal": df[animal_id].to_numpy(), "time": np.asarray(numeric_time),
                             "value": values.where(donor).to_numpy()}, index=np.arange(len(df)))
        target_positions = set(positions)
        for _, group in work.groupby("animal", dropna=True, sort=False):
            group = group.dropna(subset=["time"]).sort_values("time")
            donor_rows = group[group["value"].notna()]
            if len(donor_rows) < 2:
                continue
            # Collapse duplicate visit times before interpolation.
            donor_by_time = donor_rows.groupby("time", as_index=False)["value"].median().sort_values("time")
            if len(donor_by_time) < 2:
                continue
            target_rows = group[group.index.isin(target_positions)]
            for pos, row in target_rows.iterrows():
                t = float(row["time"])
                t_min, t_max = float(donor_by_time["time"].min()), float(donor_by_time["time"].max())
                # Do not extrapolate beyond observed in-range measurements.
                if t_min <= t <= t_max:
                    estimates.iloc[pos] = float(np.interp(
                        t, donor_by_time["time"].to_numpy(dtype=float),
                        donor_by_time["value"].to_numpy(dtype=float)))
    else:
        raise ValueError("Choose a supported estimation method.")

    missing_estimates = [p for p in positions if pd.isna(estimates.iloc[p]) or not np.isfinite(estimates.iloc[p])]
    if missing_estimates:
        raise ValueError(
            f"Could not estimate {len(missing_estimates)} selected value(s) using {method}. "
            "Choose another method or review the grouping / repeated-measure structure."
        )
    replacements = [float(estimates.iloc[p]) for p in positions]
    result[variable] = pd.to_numeric(result[variable], errors="coerce").astype(float)
    for pos, replacement in zip(positions, replacements):
        result.iat[pos, result.columns.get_loc(variable)] = replacement
    audit["replacement_values"] = replacements
    audit["records_after"] = int(len(result))
    return result, audit
