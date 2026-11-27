"""Release 6 integrated research workflows.

Methods are explicit about observational units. These utilities do not replace
prespecified protocols or independent biological interpretation.
"""
from __future__ import annotations
import hashlib, json, platform
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score,
                             accuracy_score, balanced_accuracy_score, f1_score)
from sklearn.model_selection import GroupKFold, learning_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def fit_random_slope_model(df, outcome, time_col, group_col, fixed_effects=None, reml=True):
    """Gaussian mixed model with correlated random intercept and time slope."""
    import statsmodels.formula.api as smf
    fixed_effects = fixed_effects or []
    needed = list(dict.fromkeys([outcome, time_col, group_col] + fixed_effects))
    d = df[needed].copy()
    for c in [outcome, time_col]: d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna()
    if d[group_col].nunique() < 8:
        raise ValueError("Random-slope estimation requires at least eight independent groups as a practical minimum.")
    if (d.groupby(group_col)[time_col].nunique() < 2).any():
        d = d.groupby(group_col).filter(lambda g: g[time_col].nunique() >= 2)
    if d[group_col].nunique() < 8:
        raise ValueError("Fewer than eight groups have at least two distinct time points.")
    q = lambda c: "Q(" + repr(str(c)) + ")"
    terms = [q(c) if pd.api.types.is_numeric_dtype(d[c]) else f"C({q(c)})" for c in fixed_effects]
    formula = f"{q(outcome)} ~ {q(time_col)}" + (" + " + " + ".join(terms) if terms else "")
    model = smf.mixedlm(formula, data=d, groups=d[group_col], re_formula=f"~{q(time_col)}")
    # Try a derivative-free optimizer if the default optimizer does not converge.
    first = model.fit(reml=reml, method="lbfgs", disp=False)
    if not bool(getattr(first, "converged", False)):
        second = model.fit(reml=reml, method="powell", disp=False)
        if bool(getattr(second, "converged", False)):
            first = second
    return first, d


def consensus_clustering(profiles: pd.DataFrame, n_clusters=3, n_resamples=200,
                         sample_fraction=.8, random_state=42):
    """Consensus K-means via repeated subsampling; returns co-association matrix."""
    if profiles.shape[0] < max(10, n_clusters + 2):
        raise ValueError("Consensus clustering requires at least ten animal profiles.")
    if not 2 <= int(n_clusters) < profiles.shape[0]:
        raise ValueError("n_clusters must be >=2 and smaller than the number of profiles.")
    if n_resamples < 50 or not 0.5 <= sample_fraction <= 1:
        raise ValueError("Use at least 50 resamples and a sample fraction between 0.5 and 1.")
    x = SimpleImputer(strategy="median").fit_transform(profiles.apply(pd.to_numeric, errors="coerce"))
    x = StandardScaler().fit_transform(x)
    n = len(x); rng = np.random.default_rng(random_state)
    together = np.zeros((n, n), dtype=float); observed = np.zeros((n, n), dtype=float)
    m = max(int(np.ceil(n * sample_fraction)), int(n_clusters) + 2)
    for _ in range(int(n_resamples)):
        idx = np.sort(rng.choice(n, size=min(m, n), replace=False))
        labels = KMeans(n_clusters=int(n_clusters), n_init=10,
                        random_state=int(rng.integers(0, 2**31 - 1))).fit_predict(x[idx])
        observed[np.ix_(idx, idx)] += 1
        together[np.ix_(idx, idx)] += (labels[:, None] == labels[None, :])
    consensus = np.divide(together, observed, out=np.zeros_like(together), where=observed > 0)
    np.fill_diagonal(consensus, 1.0)
    # Consensus distance is 1 - co-association; average linkage yields final labels.
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import squareform
    distance = np.clip(1 - consensus, 0, 1)
    labels = fcluster(linkage(squareform(distance, checks=False), method="average"),
                      t=int(n_clusters), criterion="maxclust")
    matrix = pd.DataFrame(consensus, index=profiles.index, columns=profiles.index)
    assignments = pd.DataFrame({"animal_id": profiles.index, "consensus_cluster": labels})
    return assignments, matrix


def external_regression_validation(estimator, external_df, outcome, features):
    """Evaluate a frozen estimator on independent external data; never refits."""
    missing = [c for c in [outcome] + list(features) if c not in external_df]
    if missing: raise ValueError(f"External dataset is missing required columns: {missing}")
    d = external_df[[outcome] + list(features)].copy()
    d[outcome] = pd.to_numeric(d[outcome], errors="coerce")
    d = d.dropna(subset=[outcome])
    if len(d) < 5: raise ValueError("At least five external observations with outcomes are required.")
    pred = np.asarray(estimator.predict(d[list(features)]), dtype=float)
    if len(pred) != len(d) or not np.isfinite(pred).all():
        raise ValueError("Estimator returned invalid or misaligned predictions.")
    y = d[outcome].to_numpy(float); resid = y - pred
    slope, intercept, r, _, _ = stats.linregress(pred, y) if np.unique(pred).size > 1 else (np.nan, np.nan, np.nan, np.nan, np.nan)
    return {"n_external": int(len(d)), "mae": float(mean_absolute_error(y, pred)),
            "rmse": float(np.sqrt(mean_squared_error(y, pred))),
            "r2": float(r2_score(y, pred)) if len(y) > 1 else np.nan,
            "mean_error_observed_minus_predicted": float(resid.mean()),
            "calibration_intercept": float(intercept), "calibration_slope": float(slope),
            "note": "Estimator was evaluated without refitting. Confirm independence of farms/herds/sites and harmonisation of measurement protocols before interpreting as external validation."}


def grouped_learning_curve(estimator, X, y, groups, cv_splits=5, train_sizes=None):
    """Group-aware learning curve; preprocessing must be inside estimator pipeline."""
    groups = np.asarray(groups)
    if len(np.unique(groups)) < 3: raise ValueError("At least three independent groups are required.")
    cv = GroupKFold(n_splits=min(int(cv_splits), len(np.unique(groups))))
    sizes = train_sizes or np.linspace(.2, 1.0, 5)
    sizes, train_scores, test_scores = learning_curve(
        clone(estimator), X, y, groups=groups, cv=cv, train_sizes=sizes,
        scoring="neg_root_mean_squared_error", n_jobs=-1, shuffle=False)
    return pd.DataFrame({"training_examples": sizes,
        "train_rmse_mean": -train_scores.mean(axis=1), "train_rmse_sd": train_scores.std(axis=1),
        "validation_rmse_mean": -test_scores.mean(axis=1), "validation_rmse_sd": test_scores.std(axis=1)})


def feature_selection_stability(X, y, estimator, groups, n_resamples=50, top_k=10, random_state=42):
    """Group-bootstrap feature importance selection frequency for tree estimators."""
    groups = np.asarray(groups); unique = np.unique(groups)
    if len(unique) < 5: raise ValueError("At least five independent groups are required.")
    if n_resamples < 20: raise ValueError("Use at least 20 resamples for stability screening.")
    rng = np.random.default_rng(random_state); counts = pd.Series(0, index=X.columns, dtype=float)
    for _ in range(int(n_resamples)):
        sampled = rng.choice(unique, size=len(unique), replace=True)
        idx = np.concatenate([np.flatnonzero(groups == g) for g in sampled])
        model = clone(estimator).fit(X.iloc[idx], np.asarray(y)[idx])
        fitted = model[-1] if hasattr(model, "steps") else model
        imp = getattr(fitted, "feature_importances_", None)
        if imp is None or len(imp) != X.shape[1]:
            raise ValueError("Estimator must expose feature_importances_ aligned to the supplied columns; preprocess externally if needed.")
        selected = np.argsort(imp)[-min(int(top_k), X.shape[1]):]
        counts.iloc[selected] += 1
    out = pd.DataFrame({"feature": counts.index, "selection_frequency": counts.values / n_resamples})
    return out.sort_values("selection_frequency", ascending=False).reset_index(drop=True)


def dataset_validation_report(df: pd.DataFrame) -> dict:
    """Non-destructive structural and numeric integrity report."""
    issues = []
    if not isinstance(df, pd.DataFrame): raise TypeError("Expected a pandas DataFrame.")
    if df.empty: issues.append("Dataset contains no records.")
    if len(df.columns) < 2: issues.append("At least two columns are expected.")
    if df.columns.duplicated().any(): issues.append("Duplicate column names detected.")
    blank = [str(c) for c in df.columns if not str(c).strip()]
    if blank: issues.append("Blank column names detected.")
    all_empty = int(df.isna().all(axis=1).sum())
    if all_empty: issues.append(f"{all_empty} fully empty rows detected.")
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    nonfinite = {str(c): int((~np.isfinite(df[c].dropna())).sum()) for c in numeric_cols}
    nonfinite = {k:v for k,v in nonfinite.items() if v}
    if nonfinite: issues.append("Non-finite numeric values detected (infinity/-infinity).")
    return {"n_records": int(len(df)), "n_variables": int(len(df.columns)),
            "duplicate_rows": int(df.duplicated().sum()), "missing_cells": int(df.isna().sum().sum()),
            "all_empty_rows": all_empty, "nonfinite_numeric_values": nonfinite,
            "issues": issues, "valid_structure": not issues}


def create_reproducibility_manifest(df, analysis_name, parameters, dataset_name=None,
                                    seed=42, software_versions=None):
    """Create JSON-serialisable analysis provenance without embedding raw data."""
    from analysis_engine.data_provenance import dataframe_fingerprint
    versions = software_versions or {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__}
    return {"analysis_name": str(analysis_name), "created_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_name": dataset_name, "dataset_fingerprint": dataframe_fingerprint(df),
            "n_records": int(len(df)), "n_variables": int(df.shape[1]),
            "parameters": parameters, "random_seed": int(seed), "software_versions": versions,
            "interpretation": "Manifest records computational provenance; it does not establish measurement validity or independent validation."}


def estimate_repeatability_icc(panel: pd.DataFrame, model: str = "ICC3", n_boot: int = 1000,
                               confidence: float = 0.95, random_state: int = 42) -> dict:
    """Compatibility wrapper for the canonical balanced-panel ICC engine."""
    from .reliability import estimate_balanced_panel_icc
    return estimate_balanced_panel_icc(panel, model=model, n_boot=n_boot,
                                       confidence=confidence, random_state=random_state)



def within_between_variability(panel: pd.DataFrame) -> dict:
    """Compatibility wrapper for the canonical balanced-panel variance decomposition."""
    from .reliability import within_between_variability as _within_between_variability
    return _within_between_variability(panel)



def bland_altman_summary(first, second, n_boot: int = 1000, confidence: float = 0.95,
                         random_state: int = 42) -> dict:
    """Compatibility wrapper for canonical paired Bland–Altman statistics."""
    from .reliability import bland_altman_paired
    _, result = bland_altman_paired(first, second, n_boot=n_boot, confidence=confidence,
                                    random_state=random_state, min_pairs=10)
    return result

