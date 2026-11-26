"""Robust population-average inference and sensitivity utilities.

These routines keep the independent sampling unit explicit (typically animal).
They do not turn observational contrasts into causal effects.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests


def _formula(df: pd.DataFrame, outcome: str, predictors: list[str]) -> str:
    terms = []
    for col in predictors:
        if col not in df.columns:
            raise ValueError(f"Predictor not found: {col}")
        if df[col].nunique(dropna=True) < 2:
            raise ValueError(f"Predictor {col!r} has fewer than two observed values.")
        is_cat = (pd.api.types.is_object_dtype(df[col]) or
                  isinstance(df[col].dtype, pd.CategoricalDtype) or
                  pd.api.types.is_bool_dtype(df[col]))
        terms.append(f'C(Q("{col}"))' if is_cat else f'Q("{col}")')
    return f'Q("{outcome}") ~ ' + (" + ".join(terms) if terms else "1")


def fit_population_average_gee(df: pd.DataFrame, outcome: str, predictors: list[str],
                               cluster_col: str, covariance: str = "exchangeable"):
    """Fit Gaussian identity-link GEE with robust sandwich covariance.

    Supported working correlations are independence and exchangeable. Inference
    is population-average; robust covariance protects asymptotically against a
    misspecified working correlation, not a small number of independent clusters.
    """
    if covariance not in {"independence", "exchangeable"}:
        raise ValueError("Choose independence or exchangeable working correlation.")
    if len(set([outcome, cluster_col] + list(predictors))) != 2 + len(set(predictors)):
        raise ValueError("Outcome, cluster identifier and predictors must be distinct columns.")
    required = [outcome, cluster_col] + list(predictors)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    work = df[required].copy()
    work[outcome] = pd.to_numeric(work[outcome], errors="coerce")
    work = work.replace([np.inf, -np.inf], np.nan).dropna()
    if work[cluster_col].nunique() < 5:
        raise ValueError("At least five independent clusters are required; substantially more are preferable for robust GEE inference.")
    if len(work) < max(20, 5 * (len(predictors) + 1)):
        raise ValueError("Insufficient complete records for the selected GEE model.")
    corr = sm.cov_struct.Exchangeable() if covariance == "exchangeable" else sm.cov_struct.Independence()
    model = smf.gee(_formula(work, outcome, predictors), groups=work[cluster_col],
                    data=work, family=sm.families.Gaussian(), cov_struct=corr)
    result = model.fit(cov_type="robust")
    audit = {"n_records": int(len(work)), "n_clusters": int(work[cluster_col].nunique()),
             "covariance": covariance, "converged": bool(getattr(result, "converged", True)),
             "estimand": "population-average marginal mean association",
             "caution": "Robust sandwich inference is asymptotic in the number of independent clusters. With few clusters, standard errors and p-values may be unreliable."}
    return result, work, audit


def fit_cluster_robust_ols(df: pd.DataFrame, outcome: str, predictors: list[str],
                           cluster_col: str):
    """OLS coefficients with animal/cluster-robust sandwich covariance."""
    required = [outcome, cluster_col] + list(predictors)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    work = df[required].copy()
    work[outcome] = pd.to_numeric(work[outcome], errors="coerce")
    work = work.replace([np.inf, -np.inf], np.nan).dropna()
    n_clusters = int(work[cluster_col].nunique())
    if n_clusters < 5:
        raise ValueError("At least five independent clusters are required; fewer clusters need specialist small-sample methods.")
    if len(work) < max(20, 5 * (len(predictors) + 1)):
        raise ValueError("Insufficient complete observations for cluster-robust regression.")
    fit = smf.ols(_formula(work, outcome, predictors), data=work).fit(
        cov_type="cluster", cov_kwds={"groups": work[cluster_col], "use_correction": True})
    return fit, work, {"n_records": int(len(work)), "n_clusters": n_clusters,
                        "covariance": "cluster sandwich with finite-sample correction",
                        "caution": "Cluster-robust covariance does not correct confounding, model misspecification or dependence between clusters."}


def missingness_audit(df: pd.DataFrame, columns: list[str], cluster_col: str | None = None):
    """Summarise variable- and cluster-level missingness without assuming MCAR."""
    cols = list(dict.fromkeys(columns + ([cluster_col] if cluster_col else [])))
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if not columns:
        raise ValueError("Select at least one analysis variable.")
    audit = pd.DataFrame([{"variable": c, "n_missing": int(df[c].isna().sum()),
                           "missing_percent": float(100 * df[c].isna().mean()),
                           "n_observed": int(df[c].notna().sum())} for c in columns])
    patterns = (df[columns].isna().astype(int).astype(str).agg("".join, axis=1)
                .value_counts().rename_axis("missingness_pattern").reset_index(name="n_records"))
    cluster_summary = None
    if cluster_col:
        per = df.groupby(cluster_col, dropna=True)[columns].agg(lambda x: x.isna().mean())
        cluster_summary = pd.DataFrame({"clusters": [int(len(per))],
            "clusters_with_any_missing": [int((per.max(axis=1) > 0).sum())],
            "median_within_cluster_missing_percent": [float(100 * per.mean(axis=1).median())]})
    return audit, patterns, cluster_summary, {
        "n_records": int(len(df)), "complete_case_records": int(df[columns].notna().all(axis=1).sum()),
        "complete_case_percent": float(100 * df[columns].notna().all(axis=1).mean()),
        "note": "Descriptive missingness audit only. It does not establish MCAR/MAR/MNAR; complete-case analysis may be biased when missingness depends on observed or unobserved values."}


def delta_adjusted_group_sensitivity(df: pd.DataFrame, outcome: str, group_col: str,
                                     group_a, group_b, deltas=(-1.0, -0.5, 0.0, 0.5, 1.0)):
    """Pattern-mixture delta sensitivity for missing outcomes in two groups.

    Missing outcomes are shifted by delta times the pooled observed outcome SD
    within each group. This is a transparent sensitivity scenario, not imputation
    under an identified missing-data mechanism. The contrast is record-weighted.
    """
    if outcome not in df or group_col not in df:
        raise ValueError("Outcome and grouping columns must exist in the dataset.")
    d = df[[outcome, group_col]].copy()
    d[outcome] = pd.to_numeric(d[outcome], errors="coerce")
    d = d.loc[d[group_col].isin([group_a, group_b])]
    observed = d[outcome].dropna()
    if len(observed) < 10:
        raise ValueError("At least ten observed outcomes across the two groups are required.")
    pooled_sd = float(observed.std(ddof=1))
    if not np.isfinite(pooled_sd) or pooled_sd <= 0:
        raise ValueError("Observed outcome standard deviation must be positive.")
    rows = []
    for delta in deltas:
        means = {}
        missing_counts = {}
        for level in (group_a, group_b):
            values = d.loc[d[group_col] == level, outcome]
            n_miss = int(values.isna().sum())
            adjusted = values.fillna(float(values.mean()) + float(delta) * pooled_sd)
            if adjusted.empty or values.notna().sum() < 3:
                raise ValueError(f"Group {level!r} needs at least three observed outcomes.")
            means[level] = float(adjusted.mean())
            missing_counts[level] = n_miss
        rows.append({"delta_sd": float(delta), "mean_a_adjusted": means[group_a],
                     "mean_b_adjusted": means[group_b], "difference_a_minus_b": means[group_a] - means[group_b],
                     "missing_a": missing_counts[group_a], "missing_b": missing_counts[group_b]})
    return pd.DataFrame(rows), {"pooled_observed_sd": pooled_sd,
        "group_a": str(group_a), "group_b": str(group_b),
        "note": "Delta shifts are applied to missing outcomes relative to each group's observed mean. These are hypothetical MNAR sensitivity scenarios; they do not recover missing values or prove a missingness mechanism. Results are record-weighted."}


def adjust_multiple_comparisons(results: pd.DataFrame, p_col: str = "p_value",
                                method: str = "fdr_bh") -> pd.DataFrame:
    """Add adjusted p-values while retaining missing p-values as missing."""
    methods = {"fdr_bh", "holm", "bonferroni", "fdr_by", "sidak", "holm-sidak"}
    if method not in methods:
        raise ValueError(f"Unsupported adjustment method. Choose from: {', '.join(sorted(methods))}")
    if p_col not in results:
        raise ValueError(f"P-value column not found: {p_col}")
    out = results.copy()
    p = pd.to_numeric(out[p_col], errors="coerce")
    valid = p.notna()
    if ((p[valid] < 0) | (p[valid] > 1)).any():
        raise ValueError("P-values must lie between zero and one.")
    out["p_adjusted"] = np.nan
    out["reject_adjusted"] = False
    if valid.any():
        reject, adjusted, _, _ = multipletests(p[valid].to_numpy(float), method=method)
        out.loc[valid, "p_adjusted"] = adjusted
        out.loc[valid, "reject_adjusted"] = reject
    out["adjustment_method"] = method
    out["n_tests_adjusted"] = int(valid.sum())
    return out
