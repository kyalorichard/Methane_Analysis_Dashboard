"""Canonical reliability and agreement computations for methane phenotypes.

UI modules should call these functions through ``service_registry``.  The
balanced-panel ICC and unbalanced long-format ICC are intentionally separate:
they answer different design questions and must never be silently substituted.
"""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd


def build_subject_occasion_panel(
    df: pd.DataFrame,
    subject_col: str,
    occasion_col: str,
    value_col: str,
    aggregation: str = "median",
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Build one value per subject × occasion and report panel completeness."""
    if aggregation not in {"mean", "median"}:
        raise ValueError("aggregation must be 'mean' or 'median'.")
    missing = [c for c in (subject_col, occasion_col, value_col) if c not in df.columns]
    if missing:
        raise KeyError(f"Columns not found: {missing}")
    d = df[[subject_col, occasion_col, value_col]].copy()
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
    d = d.replace([np.inf, -np.inf], np.nan).dropna()
    if d.empty:
        raise ValueError("No complete subject, occasion and phenotype records are available.")
    duplicate_cells = int(d.duplicated([subject_col, occasion_col]).sum())
    panel = d.pivot_table(index=subject_col, columns=occasion_col, values=value_col, aggfunc=aggregation)
    complete = panel.dropna(axis=0, how="any")
    audit = {
        "n_subjects": int(panel.shape[0]),
        "n_occasions": int(panel.shape[1]),
        "n_complete_subjects": int(complete.shape[0]),
        "n_incomplete_subjects": int(panel.shape[0] - complete.shape[0]),
        "duplicate_subject_occasion_rows_aggregated": duplicate_cells,
        "n_valid_records": int(len(d)),
    }
    return panel, audit


def estimate_balanced_panel_icc(
    panel: pd.DataFrame,
    model: str = "ICC3",
    n_boot: int = 1000,
    confidence: float = 0.95,
    random_state: int = 42,
) -> dict[str, Any]:
    """Estimate ICC(1), ICC(2), or ICC(3) from a complete subject × occasion panel."""
    if not isinstance(panel, pd.DataFrame):
        raise TypeError("panel must be a pandas DataFrame with subjects as rows and occasions as columns.")
    model = str(model).upper()
    if model not in {"ICC1", "ICC2", "ICC3"}:
        raise ValueError("model must be ICC1, ICC2 or ICC3.")
    if int(n_boot) < 200:
        raise ValueError("Use at least 200 subject-level bootstrap replicates.")
    if not 0.80 <= float(confidence) <= 0.99:
        raise ValueError("confidence must be between 0.80 and 0.99.")
    xdf = panel.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    # Preserve the legacy estimator contract: use complete subjects and expose
    # the resulting n, while the UI separately reports excluded/incomplete IDs.
    x = xdf.dropna(axis=0, how="any").to_numpy(float)
    n, k = x.shape
    if n < 5 or k < 2:
        raise ValueError("At least five complete subjects and two measurement occasions are required.")
    if not np.isfinite(x).all() or np.var(x) <= 0:
        raise ValueError("ICC is undefined for non-finite values or zero total variance.")

    def calculate(a: np.ndarray) -> tuple[float, float, float, float, float]:
        nn, kk = a.shape
        grand = a.mean()
        row_means, col_means = a.mean(axis=1), a.mean(axis=0)
        ss_rows = kk * np.sum((row_means - grand) ** 2)
        ss_cols = nn * np.sum((col_means - grand) ** 2)
        ss_total = np.sum((a - grand) ** 2)
        ss_error = ss_total - ss_rows - ss_cols
        ms_rows = ss_rows / (nn - 1)
        ms_cols = ss_cols / (kk - 1)
        ms_error = ss_error / ((nn - 1) * (kk - 1))
        ms_within = (ss_total - ss_rows) / (nn * (kk - 1))
        if model == "ICC1":
            denominator = ms_rows + (kk - 1) * ms_within
            single = (ms_rows - ms_within) / denominator if denominator > 0 else np.nan
        elif model == "ICC2":
            denominator = ms_rows + (kk - 1) * ms_error + kk * (ms_cols - ms_error) / nn
            single = (ms_rows - ms_error) / denominator if denominator > 0 else np.nan
        else:
            denominator = ms_rows + (kk - 1) * ms_error
            single = (ms_rows - ms_error) / denominator if denominator > 0 else np.nan
        average = kk * single / (1 + (kk - 1) * single) if np.isfinite(single) and abs(1 + (kk - 1) * single) > 1e-12 else np.nan
        return float(single), float(average), float(ms_rows), float(ms_cols), float(ms_error)

    single, average, ms_subjects, ms_occasions, ms_error = calculate(x)
    rng = np.random.default_rng(random_state)
    draws = []
    for _ in range(int(n_boot)):
        sample = x[rng.integers(0, n, size=n)]
        value = calculate(sample)[0]
        if np.isfinite(value):
            draws.append(value)
    if len(draws) < max(100, int(n_boot * 0.5)):
        raise ValueError("Too few valid bootstrap replicates; inspect sample size and variance structure.")
    alpha = 1 - float(confidence)
    lo, hi = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
    descriptions = {
        "ICC1": "One-way random-effects, absolute agreement; occasions are not modelled as a shared crossed factor.",
        "ICC2": "Two-way random-effects, absolute agreement; inference generalises to comparable measurement occasions.",
        "ICC3": "Two-way mixed-effects, consistency; inference is conditional on the specific occasions used.",
    }
    return {
        "model": model, "n_subjects": int(n), "n_occasions": int(k),
        "icc_single": float(single), "icc_average": float(average),
        "ci_level": float(confidence), "icc_single_ci_low": float(lo),
        "icc_single_ci_high": float(hi), "bootstrap_valid": int(len(draws)),
        "ms_subjects": ms_subjects, "ms_occasions": ms_occasions, "ms_error": ms_error,
        "interpretation": descriptions[model],
        "caution": "ICC is design- and population-dependent, is not heritability, and assumes independent subjects. Clustered subjects may require resampling at herd/site level.",
    }


def estimate_long_format_icc1(
    df: pd.DataFrame,
    subject_col: str,
    value_col: str,
    min_repeats: int = 2,
) -> dict[str, Any]:
    """One-way random-effects ICC(1,1) for unbalanced long-format replicates."""
    if subject_col not in df or value_col not in df:
        raise KeyError("Subject and phenotype columns must exist in the dataframe.")
    d = df[[subject_col, value_col]].copy()
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
    d[value_col] = d[value_col].replace([np.inf, -np.inf], np.nan)
    d = d.dropna(subset=[subject_col, value_col])
    counts = d.groupby(subject_col)[value_col].size()
    eligible = counts[counts >= int(min_repeats)].index
    d = d[d[subject_col].isin(eligible)]
    groups = [g[value_col].to_numpy(float) for _, g in d.groupby(subject_col)]
    if len(groups) < 3:
        raise ValueError("At least three subjects with repeated observations are required.")
    n = len(groups)
    grand = float(d[value_col].mean())
    ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
    ss_within = sum(((g - g.mean()) ** 2).sum() for g in groups)
    ms_between = ss_between / (n - 1)
    ms_within = ss_within / (len(d) - n)
    harmonic_n = n / sum(1 / len(g) for g in groups)
    denominator = ms_between + (harmonic_n - 1) * ms_within
    icc_single = (ms_between - ms_within) / denominator if denominator != 0 else np.nan
    icc_average = (ms_between - ms_within) / ms_between if ms_between != 0 else np.nan
    return {
        "n_animals": int(n), "n_records": int(len(d)),
        "mean_repeats": float(np.mean([len(g) for g in groups])),
        "min_repeats": int(min(map(len, groups))), "max_repeats": int(max(map(len, groups))),
        "MS_between": float(ms_between), "MS_within": float(ms_within),
        "ICC_single": float(icc_single), "ICC_average": float(icc_average),
        "design_note": "Unbalanced one-way random-effects ICC(1,1) using a harmonic-mean replicate-count approximation. This is not interchangeable with a two-way crossed ICC.",
    }


def bootstrap_long_format_icc1(df, subject_col, value_col, n_boot=500, seed=42):
    """Subject-cluster bootstrap interval for long-format ICC(1,1)."""
    rng = np.random.default_rng(seed)
    ids = pd.Series(df[subject_col].dropna().unique())
    if len(ids) < 4:
        raise ValueError("At least four subjects are required for subject-level bootstrap.")
    values = []
    for _ in range(int(n_boot)):
        sampled = rng.choice(ids.to_numpy(), size=len(ids), replace=True)
        parts = []
        for j, subject in enumerate(sampled):
            part = df.loc[df[subject_col] == subject].copy()
            part[subject_col] = f"bootstrap_{j}"
            parts.append(part)
        try:
            values.append(estimate_long_format_icc1(pd.concat(parts, ignore_index=True), subject_col, value_col)["ICC_single"])
        except (ValueError, ZeroDivisionError):
            continue
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < max(30, int(n_boot * 0.5)):
        raise ValueError("Too few valid bootstrap replicates.")
    return {"estimate": float(np.median(values)), "ci_low": float(np.quantile(values, .025)),
            "ci_high": float(np.quantile(values, .975)), "valid_bootstraps": int(len(values)), "n_boot": int(n_boot)}


def bland_altman_paired(first, second, n_boot=1000, confidence=0.95, random_state=42, min_pairs=10):
    """Canonical paired Bland–Altman statistics with pair-level bootstrap CIs."""
    a = pd.to_numeric(pd.Series(first), errors="coerce")
    b = pd.to_numeric(pd.Series(second), errors="coerce")
    d = pd.DataFrame({"first": a, "second": b}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < int(min_pairs):
        raise ValueError(f"At least {min_pairs} complete paired observations are required.")
    if int(n_boot) < 200:
        raise ValueError("Use at least 200 bootstrap replicates.")
    if not 0.80 <= float(confidence) <= 0.99:
        raise ValueError("confidence must be between 0.80 and 0.99.")
    x = d["first"].to_numpy(float)
    y = d["second"].to_numpy(float)
    means = (x + y) / 2
    differences = x - y
    bias = float(differences.mean())
    sd = float(differences.std(ddof=1))
    lower, upper = bias - 1.96 * sd, bias + 1.96 * sd
    rng = np.random.default_rng(random_state)
    draws = np.empty((int(n_boot), 3), dtype=float)
    for i in range(int(n_boot)):
        sample = rng.choice(differences, size=len(differences), replace=True)
        m, s = float(sample.mean()), float(sample.std(ddof=1))
        draws[i] = (m, m - 1.96 * s, m + 1.96 * s)
    alpha = 1 - float(confidence)
    ci = np.quantile(draws, [alpha / 2, 1 - alpha / 2], axis=0)
    pairs = pd.DataFrame({"pair_mean": means, "difference_first_minus_second": differences})
    summary = {
        "n_pairs": int(len(differences)), "bias_first_minus_second": bias,
        "sd_of_differences": sd, "lower_limit_of_agreement": float(lower),
        "upper_limit_of_agreement": float(upper), "ci_level": float(confidence),
        "bias_ci": [float(ci[0, 0]), float(ci[1, 0])],
        "lower_loa_ci": [float(ci[0, 1]), float(ci[1, 1])],
        "upper_loa_ci": [float(ci[0, 2]), float(ci[1, 2])],
        "note": "Limits are bias ±1.96 SD. Inspect proportional bias and heteroscedasticity. Bootstrap assumes independent pairs.",
    }
    return pairs, summary


def bland_altman_long_format(df, subject_col, value_col, occasion_col, occasion_a, occasion_b):
    """Pair two occasions by subject and compute the canonical agreement statistics."""
    d = df[[subject_col, occasion_col, value_col]].copy()
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
    d[value_col] = d[value_col].replace([np.inf, -np.inf], np.nan).dropna()
    wide = d.groupby([subject_col, occasion_col])[value_col].mean().unstack(occasion_col)
    if occasion_a not in wide or occasion_b not in wide:
        raise ValueError("Both selected occasions must be present.")
    paired = wide[[occasion_a, occasion_b]].dropna()
    pairs, summary = bland_altman_paired(paired[occasion_a], paired[occasion_b], min_pairs=3)
    pairs.insert(0, subject_col, paired.index.to_numpy())
    summary["occasion_a"] = str(occasion_a)
    summary["occasion_b"] = str(occasion_b)
    return pairs.rename(columns={"pair_mean": "animal_mean", "difference_first_minus_second": "difference_a_minus_b"}), summary


def within_between_variability(panel: pd.DataFrame) -> dict[str, Any]:
    """Method-of-moments variance decomposition for a balanced complete panel."""
    xdf = panel.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    x = xdf.dropna(axis=0, how="any").to_numpy(float)
    n, k = x.shape
    if n < 5 or k < 2:
        raise ValueError("At least five complete subjects and two occasions are required.")
    grand = x.mean()
    means = x.mean(axis=1)
    ms_between = k * np.sum((means - grand) ** 2) / (n - 1)
    ms_within = np.sum((x - means[:, None]) ** 2) / (n * (k - 1))
    within = float(ms_within)
    between = float(max((ms_between - ms_within) / k, 0.0))
    total = between + within
    return {
        "n_subjects": int(n), "n_occasions": int(k),
        "between_subject_variance": between, "within_subject_variance": within,
        "total_variance": float(total),
        "between_subject_fraction": between / total if total > 0 else np.nan,
        "within_subject_fraction": within / total if total > 0 else np.nan,
        "note": "Balanced-panel method-of-moments decomposition. Within-subject variance includes occasion effects and residual variation; it is not pure measurement error.",
    }


def estimate_mixed_model_icc(
    df: pd.DataFrame,
    subject_col: str,
    value_col: str,
    occasion_col: str | None = None,
    n_boot: int = 200,
    confidence: float = 0.95,
    random_state: int = 42,
    reml: bool = True,
) -> dict[str, Any]:
    """Estimate an occasion-adjusted random-intercept ICC for long/unbalanced data.

    The estimand is Var(subject intercept) / [Var(subject intercept) + Var(residual)].
    If ``occasion_col`` is supplied, occasion is included as a fixed effect; this
    adjusts the mean structure but does not create a random occasion component.
    Uncertainty is estimated by resampling independent subjects (cluster bootstrap).
    """
    import statsmodels.formula.api as smf

    if subject_col not in df or value_col not in df:
        raise KeyError("Subject and phenotype columns must exist in the dataframe.")
    if occasion_col is not None and occasion_col not in df:
        raise KeyError(f"Occasion column not found: {occasion_col}")
    if int(n_boot) < 50:
        raise ValueError("Use at least 50 subject-cluster bootstrap replicates.")
    if not 0.80 <= float(confidence) <= 0.99:
        raise ValueError("confidence must be between 0.80 and 0.99.")

    cols = [subject_col, value_col] + ([occasion_col] if occasion_col else [])
    d = df[cols].copy()
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
    d[value_col] = d[value_col].replace([np.inf, -np.inf], np.nan)
    d = d.dropna(subset=[subject_col, value_col] + ([occasion_col] if occasion_col else []))
    counts = d.groupby(subject_col).size()
    d = d[d[subject_col].isin(counts[counts >= 2].index)].copy()
    n_subjects = int(d[subject_col].nunique())
    if n_subjects < 5:
        raise ValueError("At least five subjects with repeated observations are required for this variance-component ICC.")
    if d[value_col].nunique() < 2:
        raise ValueError("The phenotype has no variation; ICC is undefined.")

    def fit_icc(frame: pd.DataFrame) -> tuple[float, float, float, bool]:
        # A stable internal grouping name prevents quoting problems with source columns.
        work = pd.DataFrame({"_y": frame[value_col].to_numpy(), "_subject": frame[subject_col].astype(str).to_numpy()})
        formula = "_y ~ 1"
        if occasion_col:
            work["_occasion"] = frame[occasion_col].astype(str).to_numpy()
            formula += " + C(_occasion)"
        model = smf.mixedlm(formula, work, groups=work["_subject"], re_formula="1")
        fitted = None
        for method in ("lbfgs", "powell", "bfgs", "cg"):
            try:
                candidate = model.fit(reml=reml, method=method, maxiter=1500, disp=False)
                fitted = candidate
                if candidate.converged:
                    break
            except Exception:
                continue
        if fitted is None:
            raise RuntimeError("Random-intercept variance-component model failed to fit.")
        subject_var = float(np.asarray(fitted.cov_re)[0, 0])
        residual_var = float(fitted.scale)
        total = subject_var + residual_var
        icc = subject_var / total if total > 0 else np.nan
        return float(icc), subject_var, residual_var, bool(fitted.converged)

    estimate, subject_var, residual_var, converged = fit_icc(d)
    if not np.isfinite(estimate):
        raise ValueError("The fitted variance components do not define a finite ICC.")

    rng = np.random.default_rng(random_state)
    ids = d[subject_col].drop_duplicates().to_numpy()
    draws: list[float] = []
    for b in range(int(n_boot)):
        sampled = rng.choice(ids, size=len(ids), replace=True)
        parts = []
        for j, sid in enumerate(sampled):
            part = d.loc[d[subject_col] == sid].copy()
            part[subject_col] = f"_boot_{j}"
            parts.append(part)
        try:
            val, _, _, _ = fit_icc(pd.concat(parts, ignore_index=True))
            if np.isfinite(val):
                draws.append(val)
        except Exception:
            continue
    if len(draws) < max(30, int(n_boot * 0.5)):
        raise RuntimeError("Too few valid subject-bootstrap fits; inspect group counts and variance structure.")
    alpha = 1 - float(confidence)
    lo, hi = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
    return {
        "estimand": "Random-intercept ICC = subject variance / (subject variance + residual variance)",
        "model": "Gaussian random-intercept mixed model (REML)" if reml else "Gaussian random-intercept mixed model (ML)",
        "occasion_adjustment": f"Fixed effect: {occasion_col}" if occasion_col else "None",
        "n_subjects": n_subjects,
        "n_records": int(len(d)),
        "subject_variance": subject_var,
        "residual_variance": residual_var,
        "icc": float(estimate),
        "confidence_level": float(confidence),
        "icc_ci_low": float(lo),
        "icc_ci_high": float(hi),
        "bootstrap_valid": int(len(draws)),
        "bootstrap_requested": int(n_boot),
        "converged": converged,
        "caution": "This is a model-based, occasion-adjusted consistency ICC. It assumes independent subjects, a Gaussian random-intercept structure and an adequate variance model. It is not interchangeable with balanced-panel ICC(2)/ICC(3), and it is not heritability.",
    }
