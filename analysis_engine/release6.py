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
    from analysis_engine.research_intelligence import dataframe_fingerprint
    versions = software_versions or {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__}
    return {"analysis_name": str(analysis_name), "created_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_name": dataset_name, "dataset_fingerprint": dataframe_fingerprint(df),
            "n_records": int(len(df)), "n_variables": int(df.shape[1]),
            "parameters": parameters, "random_seed": int(seed), "software_versions": versions,
            "interpretation": "Manifest records computational provenance; it does not establish measurement validity or independent validation."}


def estimate_repeatability_icc(panel: pd.DataFrame, model: str = "ICC3", n_boot: int = 1000,
                               confidence: float = 0.95, random_state: int = 42) -> dict:
    """Estimate single- and average-measure ICCs from a balanced subject x occasion panel.

    ICC1: one-way random effects; ICC2: two-way random, absolute agreement;
    ICC3: two-way mixed, consistency. Subjects are rows and measurement occasions
    are columns. Bootstrap confidence intervals resample subjects (rows), not
    individual measurements. Complete-case input is required by the ANOVA formulas.
    """
    if not isinstance(panel, pd.DataFrame):
        raise TypeError("panel must be a pandas DataFrame with subjects as rows and occasions as columns.")
    if model not in {"ICC1", "ICC2", "ICC3"}:
        raise ValueError("model must be ICC1, ICC2 or ICC3.")
    if n_boot < 200:
        raise ValueError("Use at least 200 subject-level bootstrap replicates.")
    if not 0.80 <= float(confidence) <= 0.99:
        raise ValueError("confidence must be between 0.80 and 0.99.")
    x = panel.apply(pd.to_numeric, errors="coerce").dropna(axis=0, how="any").to_numpy(float)
    n, k = x.shape
    if n < 5 or k < 2:
        raise ValueError("At least five complete subjects and two measurement occasions are required.")
    if not np.isfinite(x).all():
        raise ValueError("Panel contains non-finite values.")
    if np.var(x) <= 0:
        raise ValueError("ICC is undefined when the complete panel has zero total variance.")

    def _calculate(a):
        nn, kk = a.shape
        grand = a.mean()
        row_means = a.mean(axis=1)
        col_means = a.mean(axis=0)
        ss_rows = kk * np.sum((row_means - grand) ** 2)
        ss_cols = nn * np.sum((col_means - grand) ** 2)
        ss_total = np.sum((a - grand) ** 2)
        ss_error = ss_total - ss_rows - ss_cols
        ms_rows = ss_rows / (nn - 1)
        ms_cols = ss_cols / (kk - 1)
        ms_error = ss_error / ((nn - 1) * (kk - 1))
        ms_within = (ss_total - ss_rows) / (nn * (kk - 1))
        if model == "ICC1":
            den = ms_rows + (kk - 1) * ms_within
            single = (ms_rows - ms_within) / den if den > 0 else np.nan
        elif model == "ICC2":
            den = ms_rows + (kk - 1) * ms_error + kk * (ms_cols - ms_error) / nn
            single = (ms_rows - ms_error) / den if den > 0 else np.nan
        else:  # ICC3
            den = ms_rows + (kk - 1) * ms_error
            single = (ms_rows - ms_error) / den if den > 0 else np.nan
        average_den = 1 - single
        average = (kk * single / (1 + (kk - 1) * single)) if np.isfinite(single) and abs(average_den) > 1e-12 else np.nan
        return float(single), float(average), float(ms_rows), float(ms_cols), float(ms_error)

    single, average, ms_rows, ms_cols, ms_error = _calculate(x)
    rng = np.random.default_rng(random_state)
    draws = []
    for _ in range(int(n_boot)):
        idx = rng.integers(0, n, size=n)
        try:
            value = _calculate(x[idx])[0]
            if np.isfinite(value):
                draws.append(value)
        except (FloatingPointError, ZeroDivisionError):
            continue
    if len(draws) < max(100, int(n_boot * 0.5)):
        raise ValueError("Too few valid bootstrap replicates; inspect sample size and variance structure.")
    alpha = 1 - float(confidence)
    lo, hi = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
    return {
        "model": model, "n_subjects": int(n), "n_occasions": int(k),
        "icc_single": single, "icc_average": average,
        "ci_level": float(confidence), "icc_single_ci_low": float(lo),
        "icc_single_ci_high": float(hi), "bootstrap_valid": int(len(draws)),
        "ms_subjects": ms_rows, "ms_occasions": ms_cols, "ms_error": ms_error,
        "interpretation": {
            "ICC1": "One-way random-effects, absolute agreement; occasions are not modelled as a shared crossed factor.",
            "ICC2": "Two-way random-effects, absolute agreement; intended to generalise to comparable measurement occasions.",
            "ICC3": "Two-way mixed-effects, consistency; inference is conditional on the specific occasions used."
        }[model],
        "caution": "ICC is design- and population-dependent. Bootstrap intervals resample subjects and assume subjects are independent. Repeated measures nested within herd/site may require resampling at the higher independent sampling unit. ICC is not heritability."
    }


def within_between_variability(panel: pd.DataFrame) -> dict:
    """Method-of-moments within/between subject variance for a balanced panel."""
    x = panel.apply(pd.to_numeric, errors="coerce").dropna(axis=0, how="any").to_numpy(float)
    n, k = x.shape
    if n < 5 or k < 2:
        raise ValueError("At least five complete subjects and two occasions are required.")
    grand = x.mean()
    means = x.mean(axis=1)
    ms_between = k * np.sum((means - grand) ** 2) / (n - 1)
    ms_within = np.sum((x - means[:, None]) ** 2) / (n * (k - 1))
    within_var = float(ms_within)
    between_var = float(max((ms_between - ms_within) / k, 0.0))
    total = between_var + within_var
    return {"n_subjects": int(n), "n_occasions": int(k),
            "between_subject_variance": between_var, "within_subject_variance": within_var,
            "total_variance": float(total),
            "between_subject_fraction": between_var / total if total > 0 else np.nan,
            "within_subject_fraction": within_var / total if total > 0 else np.nan,
            "note": "Balanced complete-case one-way random-effects method-of-moments decomposition. Within-subject variance includes occasion effects and residual variation; it is not pure measurement error."}


def bland_altman_summary(first, second, n_boot: int = 1000, confidence: float = 0.95,
                         random_state: int = 42) -> dict:
    """Paired-method agreement summary with subject-pair bootstrap CIs for bias and limits."""
    a = pd.to_numeric(pd.Series(first), errors="coerce")
    b = pd.to_numeric(pd.Series(second), errors="coerce")
    d = pd.DataFrame({"first": a, "second": b}).dropna()
    if len(d) < 10:
        raise ValueError("At least ten complete paired observations are recommended for Bland-Altman analysis.")
    if n_boot < 200:
        raise ValueError("Use at least 200 bootstrap replicates.")
    if not 0.80 <= float(confidence) <= 0.99:
        raise ValueError("confidence must be between 0.80 and 0.99.")
    diff = (d["first"] - d["second"]).to_numpy(float)
    bias = float(diff.mean())
    sd = float(diff.std(ddof=1))
    lower, upper = bias - 1.96 * sd, bias + 1.96 * sd
    rng = np.random.default_rng(random_state)
    draws = np.empty((int(n_boot), 3), dtype=float)
    for i in range(int(n_boot)):
        z = rng.choice(diff, size=len(diff), replace=True)
        m, s = float(z.mean()), float(z.std(ddof=1))
        draws[i] = (m, m - 1.96 * s, m + 1.96 * s)
    alpha = 1 - float(confidence)
    ci = np.quantile(draws, [alpha / 2, 1 - alpha / 2], axis=0)
    return {"n_pairs": int(len(diff)), "bias_first_minus_second": bias,
            "sd_of_differences": sd, "lower_limit_of_agreement": float(lower),
            "upper_limit_of_agreement": float(upper), "ci_level": float(confidence),
            "bias_ci": [float(ci[0, 0]), float(ci[1, 0])],
            "lower_loa_ci": [float(ci[0, 1]), float(ci[1, 1])],
            "upper_loa_ci": [float(ci[0, 2]), float(ci[1, 2])],
            "note": "Limits of agreement are bias ±1.96 SD of paired differences. Assess proportional bias and heteroscedasticity graphically; bootstrap intervals assume independent pairs."}
