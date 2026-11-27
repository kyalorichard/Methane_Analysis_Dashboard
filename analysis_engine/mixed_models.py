"""Canonical Gaussian mixed-effects fitting service.

Supports a random intercept at the declared independent grouping unit. Random-slope
and longitudinal trajectory models remain separate methods because they have a
different covariance structure and scientific interpretation.
"""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def _q(name: str) -> str:
    return 'Q("' + str(name).replace('\\', '\\\\').replace('"', '\\"') + '")'


def fit_animal_random_intercept(df: pd.DataFrame, outcome: str, group_col: str,
                                fixed_effects: list[str] | None = None,
                                session_col: str | None = None, reml: bool = True,
                                min_records: int = 2):
    """Fit a random-intercept model with optimizer fallback and diagnostics.

    Returns ``(fitted_model, analysis_frame, diagnostics)``. The source dataframe
    is not modified. Fewer than five groups are permitted only with an explicit
    exploratory warning; fewer than two independent groups or repeated groups
    are rejected.
    """
    fixed_effects = list(fixed_effects or [])
    required = [outcome, group_col] + fixed_effects + ([session_col] if session_col else [])
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Mixed-model columns not found: {missing}")
    d = df[required].copy()
    d[outcome] = pd.to_numeric(d[outcome], errors="coerce")
    d[outcome] = d[outcome].replace([np.inf, -np.inf], np.nan)
    d = d.dropna(subset=[outcome, group_col] + fixed_effects + ([session_col] if session_col else []))
    if len(d) < int(min_records):
        raise ValueError(f"Insufficient complete observations: {len(d)}; at least {int(min_records)} required.")
    n_groups = int(d[group_col].nunique())
    if n_groups < 2:
        raise ValueError("A random-intercept model requires at least two independent groups.")
    repeated_groups = int((d.groupby(group_col).size() >= 2).sum())
    if repeated_groups < 2:
        raise ValueError("A random-intercept model requires repeated observations for at least two groups.")

    terms = []
    for col in fixed_effects:
        terms.append(f"C({_q(col)})" if (d[col].dtype == object or str(d[col].dtype).startswith("category")) else _q(col))
    if session_col:
        terms.append(f"C({_q(session_col)})")
    formula = f"{_q(outcome)} ~ " + (" + ".join(terms) if terms else "1")
    model = smf.mixedlm(formula, data=d, groups=d[group_col], re_formula="1")
    fit = None
    selected_optimizer = None
    fit_errors, fit_warnings = [], []
    for method in ("lbfgs", "powell", "bfgs", "cg", "nm"):
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                candidate = model.fit(reml=bool(reml), method=method, maxiter=2000, disp=False)
            fit_warnings.extend(str(w.message) for w in caught)
            fit, selected_optimizer = candidate, method
            if candidate.converged:
                break
            fit_errors.append(f"{method}: optimizer did not converge")
        except Exception as exc:
            fit_errors.append(f"{method}: {type(exc).__name__}: {str(exc)[:180]}")
    if fit is None:
        raise RuntimeError("Mixed-effects estimation failed with all optimizers: " + " | ".join(fit_errors))

    warnings_out = list(dict.fromkeys(fit_warnings + fit_errors))
    if n_groups < 5:
        warnings_out.append(
            f"Only {n_groups} independent groups contribute. Random-effect variance estimates "
            "and inferential statistics may be unstable with fewer than five independent animals/groups; treat results as exploratory."
        )
    if not fit.converged:
        warnings_out.append("Optimizer did not report convergence; interpret estimates cautiously.")
    diagnostics = {
        "formula": formula, "n_records": int(len(d)), "n_animals": n_groups,
        "n_repeated_groups": repeated_groups, "converged": bool(fit.converged),
        "optimizer": selected_optimizer, "reml": bool(reml),
        "log_likelihood": float(fit.llf),
        "aic": float(fit.aic) if np.isfinite(fit.aic) else None,
        "random_intercept_variance": float(np.asarray(fit.cov_re)[0, 0]),
        "residual_variance": float(fit.scale), "warnings": warnings_out,
        "interpretation": "Gaussian linear mixed-effects model with a group-level random intercept. Estimates are conditional associations, not causal effects."
    }
    fit._canonical_mixed_diagnostics = diagnostics
    return fit, d, diagnostics
