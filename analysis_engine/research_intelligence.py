"""Integrated methane research intelligence: QC, calibration, evidence and recommendations.

All diagnostics are descriptive/decision-support outputs. They do not certify biological validity.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats
from analysis_engine.data_provenance import dataframe_fingerprint
from analysis_engine.quality_control import flag_data_quality_rows


def dataset_readiness(df: pd.DataFrame, roles: dict | None = None, protocol: dict | None = None) -> dict:
    roles, protocol = roles or {}, protocol or {}
    animal = roles.get("animal_id")
    methane = roles.get("methane") or roles.get("outcome")
    duration = roles.get("recording_duration")
    date = roles.get("date")
    round_col = roles.get("round")
    checks = [
        ("Dataset loaded", not df.empty, f"{len(df):,} records"),
        ("Animal identifier mapped", bool(animal and animal in df), animal or "Map a stable animal ID"),
        ("Methane phenotype mapped", bool(methane and methane in df), methane or "Map the methane measurement variable"),
        ("Measurement units documented", bool(protocol.get("units")), protocol.get("units") or "Document units"),
        ("Instrument documented", bool(protocol.get("instrument")), protocol.get("instrument") or "Document instrument"),
        ("Calibration status documented", bool(protocol.get("calibration_status")), protocol.get("calibration_status") or "Document calibration"),
        ("Recording duration available", bool(duration and duration in df), duration or "Duration-based QC unavailable"),
        ("Repeated-measure structure available", bool((round_col and round_col in df) or (date and date in df)),
         round_col or date or "No session/date variable detected"),
        ("No exact duplicate rows", int(df.duplicated().sum()) == 0, f"{int(df.duplicated().sum())} duplicate rows"),
    ]
    completed = sum(bool(x[1]) for x in checks)
    return {"checks": checks, "completed": completed, "total": len(checks),
            "readiness_pct": round(100 * completed / len(checks), 1),
            "n_records": int(len(df)), "n_variables": int(df.shape[1]),
            "n_animals": int(df[animal].nunique()) if animal and animal in df else None,
            "missing_pct": round(float(df.isna().mean().mean() * 100), 2) if df.size else 0.0,
            "fingerprint": dataframe_fingerprint(df)}


def automated_recommendations(df: pd.DataFrame, roles: dict | None = None) -> list[dict]:
    roles = roles or {}
    recs = []
    animal = roles.get("animal_id")
    outcome = roles.get("methane") or roles.get("outcome")
    duration = roles.get("recording_duration")
    repeated = bool(animal and animal in df and df[animal].duplicated().any())
    if not animal or animal not in df:
        recs.append({"priority":"High","analysis":"Map animal identifier","reason":"Animal-level grouping, repeatability and leakage-resistant validation require a stable animal ID."})
    if not outcome or outcome not in df:
        recs.append({"priority":"High","analysis":"Map methane outcome","reason":"Select the methane measurement or phenotype and document its units."})
    elif pd.api.types.is_numeric_dtype(df[outcome]):
        recs.append({"priority":"High","analysis":"Phenotype distribution and QC","reason":f"Assess valid values, skewness, outliers and missingness for {outcome}."})
        if repeated:
            recs.append({"priority":"High","analysis":"Repeatability and mixed-effects analysis","reason":"Multiple records per animal are present; quantify within- and between-animal variation."})
        if animal and animal in df and df[animal].nunique() >= 3:
            recs.append({"priority":"High","analysis":"Animal-grouped regression benchmark","reason":"Use grouped validation so records from one animal do not occur in both training and test folds."})
    if duration and duration in df:
        recs.append({"priority":"High","analysis":"Recording-duration sensitivity","reason":"Test whether candidate methane phenotypes change with recording duration and minimum-duration thresholds."})
    else:
        recs.append({"priority":"Medium","analysis":"Document recording duration","reason":"Duration-normalisation and duration-related QC cannot be assessed without recording-time metadata."})
    if repeated:
        recs.append({"priority":"Medium","analysis":"Longitudinal trajectories","reason":"Repeated animal records allow assessment of temporal stability and emitter-rank changes."})
    numeric = df.select_dtypes(include="number").columns.tolist()
    if len(numeric) >= 3:
        recs.append({"priority":"Medium","analysis":"PCA and multivariate profiling","reason":"Multiple numeric variables are available for exploratory phenotype structure analysis."})
    if not recs:
        recs.append({"priority":"Medium","analysis":"Review measurement protocol","reason":"Confirm instrument, method, units, calibration, sampling frequency and study inclusion criteria."})
    return recs


def flag_data_quality(df: pd.DataFrame, columns: list[str] | None = None,
                      duration_col: str | None = None, min_duration: float | None = None,
                      nonnegative_columns: list[str] | None = None,
                      max_missing_pct: float = 30.0) -> pd.DataFrame:
    """Backward-compatible adapter to the central non-destructive QC engine."""
    return flag_data_quality_rows(df, columns, duration_col, min_duration,
                                   nonnegative_columns, max_missing_pct)


def calibration_diagnostics(df: pd.DataFrame, reference_col: str, measured_col: str) -> tuple[dict, pd.DataFrame]:
    """Agreement and linear calibration diagnostics using paired complete observations."""
    d = df[[reference_col, measured_col]].copy()
    d[reference_col] = pd.to_numeric(d[reference_col], errors="coerce")
    d[measured_col] = pd.to_numeric(d[measured_col], errors="coerce")
    d = d.dropna()
    if len(d) < 3:
        raise ValueError("At least three paired observations are required for calibration diagnostics.")
    ref, obs = d[reference_col].to_numpy(float), d[measured_col].to_numpy(float)
    if np.std(ref) == 0:
        raise ValueError("Reference measurements must have non-zero variation.")
    slope, intercept, r, p, se = stats.linregress(ref, obs)
    diff = obs - ref
    bias = float(np.mean(diff)); sd = float(np.std(diff, ddof=1))
    metrics = {"n_pairs": int(len(d)), "intercept": float(intercept), "slope": float(slope),
               "pearson_r": float(r), "pearson_p": float(p), "r_squared": float(r*r),
               "mean_bias_measured_minus_reference": bias,
               "sd_difference": sd, "loa_lower": bias - 1.96*sd, "loa_upper": bias + 1.96*sd,
               "mae": float(np.mean(np.abs(diff))), "rmse": float(np.sqrt(np.mean(diff**2))),
               "interpretation": "Agreement and calibration diagnostics only; acceptability requires prespecified, method-specific limits and independent validation."}
    d["mean_pair"] = (ref + obs) / 2
    d["difference_measured_minus_reference"] = diff
    d["calibrated_prediction_from_reference"] = intercept + slope * ref
    return metrics, d


def phenotype_evidence_matrix(df: pd.DataFrame, phenotypes: list[str],
                              animal_id: str | None = None,
                              duration_col: str | None = None) -> pd.DataFrame:
    """Descriptive evidence matrix; no arbitrary composite score or biological certification."""
    rows = []
    for col in phenotypes:
        if col not in df: continue
        x = pd.to_numeric(df[col], errors="coerce")
        valid = x.dropna()
        repeated_n = None
        if animal_id and animal_id in df:
            tmp = pd.DataFrame({"animal":df[animal_id], "value":x}).dropna()
            repeated_n = int((tmp.groupby("animal").size() >= 2).sum())
        duration_corr = np.nan
        if duration_col and duration_col in df:
            tmp = pd.DataFrame({"x":x, "duration":pd.to_numeric(df[duration_col],errors="coerce")}).dropna()
            if len(tmp) >= 4 and tmp["x"].nunique()>1 and tmp["duration"].nunique()>1:
                duration_corr = float(stats.spearmanr(tmp["x"],tmp["duration"]).statistic)
        rows.append({"phenotype":col, "n_valid_records":int(valid.size),
                     "missing_pct":float(x.isna().mean()*100),
                     "mean":float(valid.mean()) if len(valid) else np.nan,
                     "sd":float(valid.std()) if len(valid)>1 else np.nan,
                     "cv_pct":float(valid.std()/abs(valid.mean())*100) if len(valid)>1 and valid.mean()!=0 else np.nan,
                     "iqr_outlier_pct":float((((valid < valid.quantile(.25)-1.5*(valid.quantile(.75)-valid.quantile(.25))) |
                                                  (valid > valid.quantile(.75)+1.5*(valid.quantile(.75)-valid.quantile(.25)))).mean()*100)) if len(valid)>1 else np.nan,
                     "animals_with_repeated_records":repeated_n,
                     "spearman_with_duration":duration_corr,
                     "evidence_status":"Exploratory — requires protocol, repeatability, biological and external validation"})
    return pd.DataFrame(rows)


def compare_run_manifests(left: dict, right: dict) -> pd.DataFrame:
    """Field-level manifest comparison; only compares recorded metadata."""
    def flatten(obj, prefix=""):
        out = {}
        if isinstance(obj, dict):
            for k,v in obj.items(): out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
        elif isinstance(obj, list):
            out[prefix] = json.dumps(obj, sort_keys=True, default=str)
        else: out[prefix] = obj
        return out
    a,b=flatten(left),flatten(right)
    keys=sorted(set(a)|set(b))
    return pd.DataFrame([{"field":k,"run_1":a.get(k),"run_2":b.get(k),
                          "changed":a.get(k)!=b.get(k)} for k in keys])
