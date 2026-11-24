"""Matched grouped-CV comparison of conventional statistical and ML regressors."""
from __future__ import annotations
import time
import warnings
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, SplineTransformer
from sklearn.linear_model import LinearRegression, QuantileRegressor
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ML_MODELS = {
    "Random Forest": RandomForestRegressor(n_estimators=250, min_samples_leaf=2, n_jobs=-1, random_state=42),
    "Extra Trees": ExtraTreesRegressor(n_estimators=250, min_samples_leaf=2, n_jobs=-1, random_state=42),
    "HistGradientBoosting": HistGradientBoostingRegressor(random_state=42),
    "SVR": SVR(C=1.0, epsilon=0.1),
    "KNN": KNeighborsRegressor(n_neighbors=5, weights="distance"),
}


def _pipeline(features: pd.DataFrame, estimator, spline=False):
    numeric = [c for c in features.columns if pd.api.types.is_numeric_dtype(features[c])]
    categorical = [c for c in features.columns if c not in numeric]
    num_steps = [("impute", SimpleImputer(strategy="median"))]
    if spline:
        num_steps += [("spline", SplineTransformer(n_knots=4, degree=3, include_bias=False))]
    num_steps += [("scale", StandardScaler())]
    transformers = [("num", Pipeline(num_steps), numeric)]
    if categorical:
        transformers.append(("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical))
    prep = ColumnTransformer(transformers, remainder="drop")
    return Pipeline([("prep", prep), ("model", clone(estimator))])


def _cluster_bootstrap_difference(y, pred_a, pred_b, groups, n_boot=1000, seed=42):
    """Percentile CI for paired difference in RMSE (A minus B), resampling groups."""
    unique = pd.unique(groups)
    if len(unique) < 3:
        return {"difference_rmse_a_minus_b": np.nan, "ci_lower": np.nan, "ci_upper": np.nan,
                "bootstrap_replicates": 0, "note": "At least three independent groups are required."}
    by_group = {g: np.flatnonzero(np.asarray(groups) == g) for g in unique}
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(int(n_boot)):
        sampled = rng.choice(unique, size=len(unique), replace=True)
        idx = np.concatenate([by_group[g] for g in sampled])
        ya = np.asarray(y)[idx]
        pa, pb = np.asarray(pred_a)[idx], np.asarray(pred_b)[idx]
        vals.append(np.sqrt(np.mean((ya-pa)**2)) - np.sqrt(np.mean((ya-pb)**2)))
    point = float(np.sqrt(np.mean((np.asarray(y)-pred_a)**2)) - np.sqrt(np.mean((np.asarray(y)-pred_b)**2)))
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return {"difference_rmse_a_minus_b": point, "ci_lower": float(lo), "ci_upper": float(hi),
            "bootstrap_replicates": len(vals), "note": "Positive values favour model A having higher RMSE; negative values favour model A."}


def compare_grouped_models(df, outcome, features, group_col, selected_models=None,
                           n_splits=5, n_boot=500, random_state=42):
    """Compare conventional and ML models on exactly matched group-held-out folds.

    OLS and spline regression are included as conventional predictive baselines;
    median quantile regression is included as a robust conditional-quantile model.
    ML models are drawn from ML_MODELS. Predictions are out-of-fold only.
    """
    if not features:
        raise ValueError("Select at least one predictor.")
    if outcome in features or group_col in features:
        raise ValueError("Outcome and grouping identifier cannot be predictors.")
    d = df[[outcome, group_col] + list(features)].copy()
    d[outcome] = pd.to_numeric(d[outcome], errors="coerce")
    d = d.dropna(subset=[outcome, group_col])
    d = d.loc[np.isfinite(d[outcome])].reset_index(drop=True)
    groups = d[group_col].astype(str).to_numpy()
    n_groups = pd.Series(groups).nunique()
    if n_groups < 5:
        raise ValueError("At least five independent groups are required for matched grouped cross-validation.")
    n_splits = min(int(n_splits), int(n_groups))
    if n_splits < 3:
        raise ValueError("Use at least three grouped folds.")
    models = {
        "OLS (linear regression)": ("sklearn", LinearRegression(), False),
        "Spline regression (GAM-like)": ("sklearn", LinearRegression(), True),
        "Quantile regression (median)": ("sklearn", QuantileRegressor(quantile=0.5, alpha=0.0, solver="highs"), False),
        "GEE (exchangeable; marginal prediction)": ("gee", None, False),
        "Mixed-effects model (random intercept; fixed-effect prediction)": ("mixed", None, False),
        "Allometric power-law regression": ("allometric", None, False),
        **{k: ("sklearn", v, False) for k, v in ML_MODELS.items()},
    }
    names = list(models) if selected_models is None else list(selected_models)
    unknown = sorted(set(names)-set(models))
    if unknown:
        raise ValueError(f"Unknown comparison models: {unknown}")
    if len(names) < 2:
        raise ValueError("Select at least two models for comparison.")
    X, y = d[list(features)], d[outcome].to_numpy(dtype=float)
    splitter = GroupKFold(n_splits=n_splits)
    folds = list(splitter.split(X, y, groups))
    predictions, rows = {}, []
    for name in names:
        kind, estimator, spline = models[name]
        oof = np.full(len(d), np.nan)
        fold_errors, fold_rows = [], []
        started = time.perf_counter()
        for fold, (tr, te) in enumerate(folds, 1):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    if kind == "sklearn":
                        pipe = _pipeline(X.iloc[tr], estimator, spline=spline)
                        pipe.fit(X.iloc[tr], y[tr])
                        fold_pred = pipe.predict(X.iloc[te])
                    elif kind in ("gee", "mixed"):
                        import statsmodels.api as sm
                        import statsmodels.formula.api as smf
                        train = d.iloc[tr].copy()
                        formula_terms = [f'C(Q("{c}"))' if not pd.api.types.is_numeric_dtype(train[c]) else f'Q("{c}")' for c in features]
                        formula = f'Q("{outcome}") ~ ' + ' + '.join(formula_terms)
                        if kind == "gee":
                            fit = smf.gee(formula, groups=train[group_col], data=train,
                                cov_struct=sm.cov_struct.Exchangeable()).fit()
                        else:
                            fit = None
                            model_fit = smf.mixedlm(formula, data=train, groups=train[group_col])
                            fit_error = None
                            for optimizer in ("lbfgs", "powell", "cg"):
                                try:
                                    candidate = model_fit.fit(reml=False, method=optimizer, disp=False)
                                    if bool(getattr(candidate, "converged", False)):
                                        fit = candidate
                                        break
                                    fit_error = RuntimeError(f"Mixed-effects optimizer {optimizer} did not converge")
                                except Exception as exc:
                                    fit_error = exc
                            if fit is None:
                                raise RuntimeError(f"Mixed-effects model failed to converge: {fit_error}")
                        fold_pred = np.asarray(fit.predict(d.iloc[te]))
                    else:
                        if len(features) != 1 or not pd.api.types.is_numeric_dtype(d[features[0]]):
                            raise ValueError("Allometric regression requires exactly one numeric predictor (typically body weight).")
                        xtr = pd.to_numeric(d.iloc[tr][features[0]], errors="coerce").to_numpy(float)
                        xte = pd.to_numeric(d.iloc[te][features[0]], errors="coerce").to_numpy(float)
                        if np.any(xtr <= 0) or np.any(xte <= 0) or np.any(y[tr] <= 0):
                            raise ValueError("Allometric regression requires strictly positive predictor and outcome values.")
                        from sklearn.linear_model import LinearRegression as _LR
                        power = _LR().fit(np.log(xtr).reshape(-1, 1), np.log(y[tr]))
                        log_resid = np.log(y[tr]) - power.predict(np.log(xtr).reshape(-1, 1))
                        smearing = float(np.mean(np.exp(log_resid)))
                        fold_pred = np.exp(power.predict(np.log(xte).reshape(-1, 1))) * smearing
                oof[te] = fold_pred
                fold_rows.append({"fold": fold, "train_groups": int(pd.Series(groups[tr]).nunique()),
                                  "test_groups": int(pd.Series(groups[te]).nunique()), "test_records": int(len(te))})
            except Exception as exc:
                fold_errors.append(f"fold {fold}: {type(exc).__name__}: {str(exc)[:180]}")
        elapsed = time.perf_counter()-started
        if np.isfinite(oof).all():
            predictions[name] = oof
            rows.append({"model": name, "model_family": "Conventional statistical" if name.startswith(("OLS", "Spline", "Quantile", "GEE", "Mixed-effects", "Allometric")) else "Machine learning",
                "n_records": len(d), "n_groups": n_groups, "folds_completed": len(fold_rows),
                "RMSE": float(np.sqrt(mean_squared_error(y, oof))), "MAE": float(mean_absolute_error(y, oof)),
                "R2": float(r2_score(y, oof)), "mean_prediction_bias": float(np.mean(oof-y)),
                "median_absolute_error": float(np.median(np.abs(oof-y))), "fit_predict_seconds": elapsed,
                "status": "completed", "warnings": ""})
        else:
            rows.append({"model": name, "model_family": "Conventional statistical" if name.startswith(("OLS", "Spline", "Quantile", "GEE", "Mixed-effects", "Allometric")) else "Machine learning",
                "n_records": len(d), "n_groups": n_groups, "folds_completed": len(fold_rows),
                "fit_predict_seconds": elapsed, "status": "failed", "warnings": "; ".join(fold_errors)})
    results = pd.DataFrame(rows).sort_values("RMSE", na_position="last").reset_index(drop=True)
    pairwise = []
    completed = list(predictions)
    for i, a in enumerate(completed):
        for b in completed[i+1:]:
            ci = _cluster_bootstrap_difference(y, predictions[a], predictions[b], groups,
                                               n_boot=n_boot, seed=random_state)
            pairwise.append({"model_A": a, "model_B": b, **ci})
    oof = pd.DataFrame({"observed": y, "group": groups, **{f"pred__{k}": v for k,v in predictions.items()}})
    return {"metrics": results, "paired_comparisons": pd.DataFrame(pairwise), "oof_predictions": oof,
            "folds": n_splits, "n_groups": n_groups, "n_records": len(d),
            "interpretation": "Predictive comparison only. It does not compare causal estimands, coefficient inference, or biological mechanisms. Group bootstrap intervals quantify uncertainty under the supplied independent grouping unit."}
