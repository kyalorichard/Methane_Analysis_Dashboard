"""Shared helpers for animal-level longitudinal comparisons."""

import pandas as pd


def paired_round_changes(pivot: pd.DataFrame, baseline, comparison) -> pd.DataFrame:
    """Return complete animal-level pairs and comparison-minus-baseline change.

    The function deliberately constructs the output from Series rather than
    ``pivot[[baseline, comparison]]`` so duplicate selections can never create
    duplicate output columns. Round labels must identify exactly one column.
    """
    if baseline == comparison:
        raise ValueError("Choose two different monitoring rounds for a paired comparison.")

    positions = {}
    for label in (baseline, comparison):
        matches = [i for i, value in enumerate(pivot.columns) if value == label]
        if len(matches) != 1:
            raise ValueError(
                f"Monitoring round {label!r} must identify exactly one pivot column; "
                f"found {len(matches)}. Check the round labels in the source data."
            )
        positions[label] = matches[0]

    baseline_values = pd.to_numeric(pivot.iloc[:, positions[baseline]], errors="coerce")
    comparison_values = pd.to_numeric(pivot.iloc[:, positions[comparison]], errors="coerce")
    paired = pd.DataFrame(
        {
            "baseline_value": baseline_values,
            "comparison_value": comparison_values,
        },
        index=pivot.index,
    ).dropna(subset=["baseline_value", "comparison_value"])
    paired["change"] = paired["comparison_value"] - paired["baseline_value"]
    return paired


def prepare_longitudinal_frame(df, outcome, time_col, subject_col, fixed_effects=None,
                               treatment_col=None, time_kind="numeric"):
    """Create a complete-case long-format frame and elapsed numeric time.

    Date time is converted to elapsed days from the earliest retained date.
    Irregular and unbalanced occasions are retained; no interpolation is done.
    """
    import numpy as np
    if len({outcome, time_col, subject_col}) != 3:
        raise ValueError("Outcome, time and subject identifier must be three different columns.")
    if treatment_col in {outcome, time_col, subject_col}:
        raise ValueError("Treatment/group must be distinct from outcome, time and subject identifier.")
    if set(fixed_effects or []) & {outcome, time_col, subject_col}:
        raise ValueError("Fixed-effect covariates must be distinct from outcome, time and subject identifier.")
    required = list(dict.fromkeys([outcome, time_col, subject_col] +
                                  list(fixed_effects or []) +
                                  ([treatment_col] if treatment_col else [])))
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    work = df[required].copy()
    work[outcome] = pd.to_numeric(work[outcome], errors="coerce")
    if time_kind == "date":
        parsed = pd.to_datetime(work[time_col], errors="coerce", utc=True)
        if parsed.notna().sum() == 0:
            raise ValueError("The selected date column contains no valid dates.")
        origin = parsed.min()
        work["_time_numeric"] = (parsed - origin).dt.total_seconds() / 86400.0
        time_label = f"Elapsed days from {origin.date()}"
    else:
        work["_time_numeric"] = pd.to_numeric(work[time_col], errors="coerce")
        time_label = str(time_col)
    before = len(work)
    work = work.replace([np.inf, -np.inf], np.nan).dropna(subset=[outcome, "_time_numeric", subject_col] + list(fixed_effects or []) + ([treatment_col] if treatment_col else []))
    complete_case_records = len(work)
    if work.empty:
        raise ValueError("No complete observations remain after validating outcome, time, subject and covariates.")
    if work[subject_col].nunique() < 5:
        raise ValueError("At least five independent subjects are required for this longitudinal mixed-model workflow.")
    repeated = work.groupby(subject_col)["_time_numeric"].nunique()
    eligible = repeated[repeated >= 2].index
    work = work[work[subject_col].isin(eligible)].copy()
    model_records = len(work)
    if work[subject_col].nunique() < 5:
        raise ValueError("Fewer than five subjects have at least two distinct time points.")
    if work["_time_numeric"].nunique() < 2:
        raise ValueError("The time variable must contain at least two distinct values.")
    visit_counts = work.groupby(subject_col)["_time_numeric"].nunique()
    unequal_visit_counts = int((visit_counts != visit_counts.mode().iloc[0]).sum())
    irregular_spacing = 0
    for _, subject_frame in work.groupby(subject_col):
        times = np.sort(subject_frame["_time_numeric"].unique())
        gaps = np.diff(times)
        if len(gaps) >= 2 and not np.allclose(gaps, gaps[0], rtol=1e-5, atol=1e-8):
            irregular_spacing += 1
    work = work.rename(columns={subject_col: "_subject", outcome: "_outcome"})
    return work, {"input_records": int(before), "complete_case_records": int(complete_case_records),
                  "complete_records": int(model_records), "dropped_records": int(before - complete_case_records),
                  "excluded_nonrepeated_records": int(complete_case_records - model_records),
                  "subjects": int(work["_subject"].nunique()),
                  "subjects_with_repeats": int(work["_subject"].nunique()),
                  "time_label": time_label,
                  "subjects_with_unequal_visit_counts": unequal_visit_counts,
                  "subjects_with_irregular_spacing": int(irregular_spacing)}


def fit_longitudinal_mixed_model(df, outcome, time_col, subject_col, fixed_effects=None,
                                 treatment_col=None, time_kind="numeric", time_form="linear",
                                 spline_df=4, random_slope=True, reml=False):
    """Fit a Gaussian animal-clustered mixed model with optional spline/time interaction.

    ``time_form`` is linear or cubic B-spline. Treatment (if supplied) interacts
    with the time basis, allowing group-specific trajectories. Random slopes
    are linear in elapsed time even when the fixed time trend is nonlinear.
    """
    import statsmodels.formula.api as smf
    import warnings
    fixed_effects = list(fixed_effects or [])
    if treatment_col and treatment_col not in fixed_effects:
        fixed_effects.append(treatment_col)
    work, audit = prepare_longitudinal_frame(df, outcome, time_col, subject_col,
        fixed_effects=fixed_effects, treatment_col=treatment_col, time_kind=time_kind)
    q = lambda name: f"Q({name!r})"
    time_term = q("_time_numeric") if time_form == "linear" else f"bs({q('_time_numeric')}, df={int(spline_df)}, degree=3, include_intercept=False)"
    covariate_terms = []
    for col in fixed_effects:
        covariate_terms.append(f"C({q(col)})" if not pd.api.types.is_numeric_dtype(work[col]) else q(col))
    rhs = [time_term] + covariate_terms
    if treatment_col:
        treatment_term = f"C({q(treatment_col)})" if not pd.api.types.is_numeric_dtype(work[treatment_col]) else q(treatment_col)
        rhs.append(f"{time_term}:{treatment_term}")
    formula = f"{q('_outcome')} ~ " + " + ".join(rhs)
    random_formula = f"~{q('_time_numeric')}" if random_slope else "1"
    model = smf.mixedlm(formula, data=work, groups=work["_subject"], re_formula=random_formula)
    errors = []
    fitted = None
    for method in ("lbfgs", "powell", "bfgs", "cg"):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                candidate = model.fit(reml=bool(reml), method=method, disp=False)
            if bool(getattr(candidate, "converged", False)):
                fitted = candidate
                break
            fitted = candidate
            errors.append(f"{method}: optimizer did not converge")
        except Exception as exc:
            errors.append(f"{method}: {type(exc).__name__}: {exc}")
    if fitted is None:
        raise RuntimeError("Mixed model failed with all optimizers: " + " | ".join(errors))
    audit.update({"formula": formula, "random_effects": "random intercept + linear time slope" if random_slope else "random intercept only",
                  "converged": bool(getattr(fitted, "converged", False)), "optimizer_notes": errors,
                  "time_form": time_form, "reml": bool(reml), "treatment_interaction": bool(treatment_col)})
    return fitted, work, audit


def longitudinal_prediction_frame(result, work, n_points=100, treatment_col=None):
    """Population-level fitted trajectory and Wald 95% confidence intervals."""
    import numpy as np
    import patsy
    design_info = result.model.data.design_info
    tmin, tmax = float(work["_time_numeric"].min()), float(work["_time_numeric"].max())
    times = np.linspace(tmin, tmax, int(n_points))
    levels = list(pd.unique(work[treatment_col])) if treatment_col else [None]
    frames = []
    params = np.asarray(result.fe_params, dtype=float)
    cov = np.asarray(result.cov_params().loc[result.fe_params.index, result.fe_params.index], dtype=float)
    for level in levels:
        grid = pd.DataFrame({"_time_numeric": times})
        for col in work.columns:
            if col in {"_outcome", "_subject", "_time_numeric"}:
                continue
            if col == treatment_col and treatment_col is not None:
                grid[col] = level
            elif pd.api.types.is_numeric_dtype(work[col]):
                grid[col] = float(pd.to_numeric(work[col], errors="coerce").median())
            else:
                mode = work[col].mode(dropna=True)
                grid[col] = mode.iloc[0] if len(mode) else work[col].iloc[0]
        exog = np.asarray(patsy.build_design_matrices([design_info], grid, return_type="dataframe")[0], dtype=float)
        estimate = exog @ params
        variance = np.maximum(np.einsum("ij,jk,ik->i", exog, cov, exog), 0)
        se = np.sqrt(variance)
        pred = pd.DataFrame({"time": times, "predicted": estimate,
                             "ci_lower": estimate - 1.96 * se, "ci_upper": estimate + 1.96 * se})
        if treatment_col:
            pred[treatment_col] = str(level)
        frames.append(pred)
    return pd.concat(frames, ignore_index=True)


def longitudinal_residual_diagnostics(result, work):
    """Return row-level fitted/residual diagnostics and compact assumption checks."""
    import numpy as np
    from scipy import stats
    fitted = np.asarray(result.fittedvalues, dtype=float)
    residual = np.asarray(result.resid, dtype=float)
    scale = float(np.std(residual, ddof=1)) if len(residual) > 1 else np.nan
    standardized = residual / scale if np.isfinite(scale) and scale > 0 else np.full(len(residual), np.nan)
    diagnostic = work[["_subject", "_time_numeric"]].copy()
    diagnostic["observed"] = np.asarray(work["_outcome"], dtype=float)
    diagnostic["fitted"] = fitted
    diagnostic["residual"] = residual
    diagnostic["standardized_residual"] = standardized
    finite = residual[np.isfinite(residual)]
    shapiro_p = float(stats.shapiro(finite[:5000]).pvalue) if 3 <= len(finite) <= 5000 else np.nan
    return diagnostic, {"residual_mean": float(np.mean(finite)) if len(finite) else np.nan,
        "residual_sd": scale, "shapiro_p_value_screen": shapiro_p,
        "n_residuals": int(len(finite)),
        "caution": "Residual checks are diagnostic screens, not proof of model validity. Assess residual patterns by fitted value, time and subject; Shapiro-Wilk is sample-size sensitive."}


def compare_longitudinal_models(model_a, model_b, same_data=True, nested=False):
    """Compare fitted Gaussian mixed models; LR test only for nested ML fits."""
    import numpy as np
    rows = []
    for label, model in (("Model A", model_a), ("Model B", model_b)):
        rows.append({"model": label, "aic": float(model.aic), "bic": float(model.bic),
                     "log_likelihood": float(model.llf), "converged": bool(getattr(model, "converged", False))})
    out = pd.DataFrame(rows)
    lr = np.nan; pvalue = np.nan; df_diff = np.nan; note = "AIC/BIC are comparable only when models use the same response records and likelihood basis."
    if same_data and nested and not bool(getattr(model_a, "reml", False)) and not bool(getattr(model_b, "reml", False)):
        df_diff = abs(float(model_b.df_modelwc) - float(model_a.df_modelwc))
        lr = max(0.0, 2.0 * (float(model_b.llf) - float(model_a.llf)))
        if df_diff > 0:
            from scipy.stats import chi2
            pvalue = float(chi2.sf(lr, df_diff))
            note = "Likelihood-ratio test shown for user-declared nested models fitted by ML on identical records. Verify nesting and boundary conditions; variance-component tests can have nonstandard null distributions."
    return out, {"likelihood_ratio": lr, "df_difference": df_diff, "p_value": pvalue, "note": note}
