"""Advanced research methods for methane phenotype studies.

All routines are deliberately explicit about observational units and assumptions.
They return statistical outputs; biological interpretation remains a study-team task.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def fit_spline_additive(df: pd.DataFrame, outcome: str, smooth_terms: list[str],
                        linear_terms: list[str] | None = None, df_spline: int = 5):
    """Fit a Gaussian additive spline regression with HC3 covariance.

    Each smooth term is represented by a B-spline basis. This is a practical
    spline-additive model, not a penalised GAM; basis dimension is user supplied
    and should be checked with sensitivity analysis.
    """
    linear_terms = linear_terms or []
    if not smooth_terms:
        raise ValueError("Select at least one continuous variable for a smooth term.")
    if df_spline < 3 or df_spline > 10:
        raise ValueError("Spline degrees of freedom must be between 3 and 10.")
    cols = [outcome] + smooth_terms + linear_terms
    d = df[cols].copy()
    d[outcome] = _numeric(d[outcome])
    for c in smooth_terms:
        d[c] = _numeric(d[c])
    d = d.dropna()
    if len(d) < max(30, 5 * (len(smooth_terms) + len(linear_terms))):
        raise ValueError("Insufficient complete observations for the selected spline model.")
    terms = [f"bs(Q('{c}'), df={df_spline}, degree=3, include_intercept=False)" for c in smooth_terms]
    terms += [f"C(Q('{c}'))" if d[c].dtype == object else f"Q('{c}')" for c in linear_terms]
    model = smf.ols(f"Q('{outcome}') ~ " + " + ".join(terms), data=d).fit(cov_type="HC3")
    return model, d


def fit_random_intercept_model(df: pd.DataFrame, outcome: str, predictors: list[str],
                               group_col: str, reml: bool = True):
    """Fit a random-intercept linear mixed model grouped by animal/herd/site."""
    cols = [outcome, group_col] + predictors
    d = df[cols].copy()
    d[outcome] = _numeric(d[outcome])
    d = d.dropna()
    n_groups = int(d[group_col].nunique())
    if n_groups < 2:
        raise ValueError("A random-intercept model requires at least two independent groups.")
    repeated_groups = int((d.groupby(group_col).size() >= 2).sum())
    if repeated_groups < 2:
        raise ValueError("A random-intercept model requires repeated observations for at least two groups. Consider a fixed-effects or descriptive analysis instead.")
    if len(d) < max(20, len(predictors) + 10):
        raise ValueError("Insufficient complete observations for the mixed model.")
    terms = [f"C(Q('{c}'))" if d[c].dtype == object else f"Q('{c}')" for c in predictors]
    formula = f"Q('{outcome}') ~ " + " + ".join(terms or ["1"])
    model = smf.mixedlm(formula, data=d, groups=d[group_col]).fit(reml=reml, method="lbfgs", disp=False)
    # Preserve the caution alongside the fitted object for the UI/report layer.
    model._small_group_warning = (
        f"Only {n_groups} independent groups contributed. Random-effect variance estimates "
        "may be unstable with fewer than five groups; interpret this fit as exploratory."
        if n_groups < 5 else None
    )
    return model, d


def animal_trajectory_slopes(df: pd.DataFrame, animal_col: str, time_col: str,
                             outcome: str, min_points: int = 3) -> pd.DataFrame:
    """Estimate within-animal OLS time slopes; requires numeric time or ordinal coding."""
    d = df[[animal_col, time_col, outcome]].copy()
    d[time_col] = _numeric(d[time_col]); d[outcome] = _numeric(d[outcome])
    d = d.dropna()
    rows = []
    for animal, g in d.groupby(animal_col, sort=False):
        g = g.sort_values(time_col)
        if len(g) < min_points or g[time_col].nunique() < 2:
            continue
        fit = stats.linregress(g[time_col].to_numpy(float), g[outcome].to_numpy(float))
        rows.append({"animal_id": animal, "n_records": len(g), "time_min": g[time_col].min(),
                     "time_max": g[time_col].max(), "intercept": fit.intercept,
                     "slope_per_time_unit": fit.slope, "r_squared": fit.rvalue ** 2,
                     "p_value_slope": fit.pvalue})
    if not rows:
        raise ValueError("No animals have enough repeated observations for trajectory estimation.")
    out = pd.DataFrame(rows)
    out["p_fdr_bh"] = multipletests(out["p_value_slope"], method="fdr_bh")[1]
    return out


def multivariate_trait_associations(df: pd.DataFrame, traits: list[str], method: str = "spearman"):
    """Pairwise trait correlations with pairwise sample sizes and BH-adjusted p-values."""
    if len(traits) < 2:
        raise ValueError("Select at least two traits.")
    if method not in {"spearman", "pearson"}:
        raise ValueError("Method must be spearman or pearson.")
    rows = []
    for i, a in enumerate(traits):
        for b in traits[i + 1:]:
            x = pd.DataFrame({"a": _numeric(df[a]), "b": _numeric(df[b])}).dropna()
            if len(x) < 4:
                continue
            res = stats.spearmanr(x.a, x.b) if method == "spearman" else stats.pearsonr(x.a, x.b)
            rows.append({"trait_1": a, "trait_2": b, "n_pairs": len(x), "method": method,
                         "correlation": float(res.statistic), "p_value": float(res.pvalue)})
    if not rows:
        raise ValueError("No trait pairs have at least four paired observations.")
    out = pd.DataFrame(rows)
    out["p_fdr_bh"] = multipletests(out.p_value, method="fdr_bh")[1]
    return out


def regression_prediction_diagnostics(observed, predicted) -> dict:
    """Assess calibration and residual error for out-of-fold or held-out predictions."""
    d = pd.DataFrame({"observed": _numeric(pd.Series(observed)),
                      "predicted": _numeric(pd.Series(predicted))}).dropna()
    if len(d) < 5:
        raise ValueError("At least five paired observed/predicted values are required.")
    residual = d.observed - d.predicted
    slope, intercept, r, p, se = stats.linregress(d.predicted, d.observed)
    return {"n": len(d), "mae": float(np.mean(np.abs(residual))),
            "rmse": float(np.sqrt(np.mean(residual ** 2))),
            "mean_error_observed_minus_predicted": float(residual.mean()),
            "calibration_intercept": float(intercept), "calibration_slope": float(slope),
            "r_squared_calibration": float(r ** 2),
            "residual_sd": float(residual.std(ddof=1)),
            "residual_q025": float(residual.quantile(.025)),
            "residual_q975": float(residual.quantile(.975)),
            "note": "Prediction intervals require an appropriate validation design; residual quantiles are descriptive and are not guaranteed coverage intervals."}


def variance_components_mixedlm(model) -> pd.DataFrame:
    """Extract random-intercept and residual variance from a fitted statsmodels MixedLM."""
    random_var = float(np.asarray(model.cov_re)[0, 0]) if np.asarray(model.cov_re).size else np.nan
    residual_var = float(model.scale)
    total = random_var + residual_var
    return pd.DataFrame([
        {"component": "Between-group random intercept", "variance": random_var,
         "proportion_total": random_var / total if total > 0 else np.nan},
        {"component": "Residual / within-group", "variance": residual_var,
         "proportion_total": residual_var / total if total > 0 else np.nan},
    ])


def fit_quantile_regression(df: pd.DataFrame, outcome: str, predictors: list[str],
                            quantile: float | None = None, settings: dict | None = None):
    """Compatibility adapter to the canonical quantile-regression engine.

    Keeps the historical ``(model, used_data)`` return contract while ensuring
    every page uses the same estimator, validation rules and formula handling.
    """
    from analysis_engine.advanced import fit_quantile_regression as _canonical
    model = _canonical(df, outcome, predictors, quantile=quantile, settings=settings)
    used = model.model.data.frame.copy()
    return model, used


def fit_allometric_scaling(df: pd.DataFrame, outcome: str, size_variable: str):
    """Fit log(outcome)=intercept+exponent*log(size), for positive measurements.

    The exponent is an estimated scaling relationship. It is not automatically
    a biological efficiency metric and requires justified units and covariates.
    """
    d = df[[outcome, size_variable]].copy()
    d[outcome] = _numeric(d[outcome]); d[size_variable] = _numeric(d[size_variable])
    d = d.dropna()
    d = d.loc[(d[outcome] > 0) & (d[size_variable] > 0)].copy()
    if len(d) < 10:
        raise ValueError("At least ten positive paired observations are required for log-log scaling.")
    d["_log_outcome"] = np.log(d[outcome])
    d["_log_size"] = np.log(d[size_variable])
    model = smf.ols("_log_outcome ~ _log_size", data=d).fit(cov_type="HC3")
    ci = model.conf_int().loc["_log_size"]
    return {
        "n": int(len(d)), "intercept": float(model.params["Intercept"]),
        "scaling_exponent": float(model.params["_log_size"]),
        "exponent_ci_low": float(ci.iloc[0]), "exponent_ci_high": float(ci.iloc[1]),
        "r_squared": float(model.rsquared), "aic": float(model.aic),
        "summary": model.summary().as_text(), "used_data": d,
        "note": "Log-log association among positive paired observations. Interpret the exponent only in the context of the measured traits, units, population and study design."
    }


def cluster_bootstrap_mean_difference(df: pd.DataFrame, outcome: str, group_col: str,
                                      group_a, group_b, animal_col: str,
                                      n_boot: int = 2000, confidence: float = 0.95,
                                      seed: int = 2026):
    """Animal-cluster bootstrap CI for difference in group means.

    Repeated records are first reduced to one animal-level mean. Animals are then
    resampled independently within each comparison group. This estimates a
    difference in animal-level means, not a repeated-record-weighted contrast.
    """
    if n_boot < 200:
        raise ValueError("Use at least 200 bootstrap replicates.")
    if not 0.80 <= float(confidence) <= 0.99:
        raise ValueError("Confidence level must be between 0.80 and 0.99.")
    d = df[[outcome, group_col, animal_col]].copy()
    d[outcome] = _numeric(d[outcome])
    d = d.dropna()
    d = d.loc[d[group_col].isin([group_a, group_b])]
    animal = d.groupby([group_col, animal_col], as_index=False)[outcome].mean()
    a = animal.loc[animal[group_col] == group_a, outcome].to_numpy(float)
    b = animal.loc[animal[group_col] == group_b, outcome].to_numpy(float)
    if len(a) < 5 or len(b) < 5:
        raise ValueError("At least five independent animals are required in each group.")
    observed = float(a.mean() - b.mean())
    rng = np.random.default_rng(seed)
    draws = np.empty(int(n_boot), dtype=float)
    for i in range(int(n_boot)):
        draws[i] = rng.choice(a, size=len(a), replace=True).mean() - rng.choice(b, size=len(b), replace=True).mean()
    alpha = 1 - float(confidence)
    lo, hi = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
    return {
        "group_a": str(group_a), "group_b": str(group_b), "n_animals_a": int(len(a)),
        "n_animals_b": int(len(b)), "mean_a": float(a.mean()), "mean_b": float(b.mean()),
        "difference_a_minus_b": observed, "confidence_level": float(confidence),
        "ci_low": float(lo), "ci_high": float(hi), "bootstrap_replicates": int(n_boot),
        "seed": int(seed), "bootstrap_distribution": draws,
        "note": "Animal-level cluster bootstrap percentile interval. The interval is descriptive/inferential under independent animal sampling within groups; it does not adjust for confounding or clustered herd/site sampling."
    }
