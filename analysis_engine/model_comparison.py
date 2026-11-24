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
from sklearn.model_selection import GroupKFold, RandomizedSearchCV, GridSearchCV, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ML_MODELS = {
    "Random Forest": RandomForestRegressor(n_estimators=250, min_samples_leaf=2, n_jobs=-1, random_state=42),
    "Extra Trees": ExtraTreesRegressor(n_estimators=250, min_samples_leaf=2, n_jobs=-1, random_state=42),
    "HistGradientBoosting": HistGradientBoostingRegressor(random_state=42),
    "SVR": SVR(C=1.0, epsilon=0.1),
    "KNN": KNeighborsRegressor(n_neighbors=5, weights="distance"),
}


def _pipeline(features: pd.DataFrame, estimator, spline=False, preprocessing=None):
    preprocessing = preprocessing or {}
    numeric = [c for c in features.columns if pd.api.types.is_numeric_dtype(features[c])]
    categorical = [c for c in features.columns if c not in numeric]
    num_steps = [("impute", SimpleImputer(strategy=preprocessing.get("numeric_imputation", "median")))]
    if spline:
        num_steps += [("spline", SplineTransformer(n_knots=4, degree=3, include_bias=False))]
    if preprocessing.get("scale_numeric", True):
        num_steps += [("scale", StandardScaler())]
    transformers = [("num", Pipeline(num_steps), numeric)]
    if categorical:
        cat_strategy = preprocessing.get("categorical_imputation", "most_frequent")
        cat_imputer = SimpleImputer(strategy=cat_strategy, fill_value="__missing__") if cat_strategy == "constant" else SimpleImputer(strategy=cat_strategy)
        transformers.append(("cat", Pipeline([("impute", cat_imputer),
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
                           n_splits=5, n_boot=500, random_state=42,
                           model_parameters=None, preprocessing=None, tune_models=False, tuning_iter=12, tuning_method="random", conventional_parameters=None):
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
    model_parameters = model_parameters or {}
    preprocessing = preprocessing or {}
    conventional_parameters = conventional_parameters or {}
    tuned_parameters = {}
    for name in names:
        kind, estimator, spline = models[name]
        if kind == "sklearn" and name in model_parameters:
            estimator = clone(estimator)
            allowed = estimator.get_params(deep=False)
            supplied = {k: v for k, v in model_parameters[name].items() if k in allowed}
            if "random_state" in allowed:
                supplied.setdefault("random_state", int(random_state))
            estimator.set_params(**supplied)
        oof = np.full(len(d), np.nan)
        fold_errors, fold_rows = [], []
        started = time.perf_counter()
        for fold, (tr, te) in enumerate(folds, 1):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    if kind == "sklearn":
                        pipe = _pipeline(X.iloc[tr], estimator, spline=spline, preprocessing=preprocessing)
                        if spline:
                            knots = int(conventional_parameters.get("spline_n_knots", 4))
                            pipe.set_params(prep__num__spline__n_knots=knots)
                        if name.startswith("Quantile"):
                            pipe.set_params(model__quantile=float(conventional_parameters.get("quantile", 0.5)))
                        if tune_models and name in ML_MODELS:
                            spaces = {
                                "Random Forest": {"model__n_estimators": [150, 300, 600], "model__max_depth": [None, 5, 10], "model__min_samples_leaf": [1, 2, 4], "model__max_features": [1.0, "sqrt", 0.7]},
                                "Extra Trees": {"model__n_estimators": [150, 300, 600], "model__max_depth": [None, 5, 10], "model__min_samples_leaf": [1, 2, 4], "model__max_features": [1.0, "sqrt", 0.7]},
                                "HistGradientBoosting": {"model__learning_rate": [0.03, 0.05, 0.1], "model__max_iter": [100, 200, 400], "model__max_leaf_nodes": [15, 31, 63], "model__l2_regularization": [0.0, 0.1, 1.0]},
                                "SVR": {"model__C": [0.1, 1.0, 10.0, 100.0], "model__epsilon": [0.01, 0.1, 0.3], "model__kernel": ["rbf", "linear"], "model__gamma": ["scale", "auto"]},
                                "KNN": {"model__n_neighbors": [3, 5, 7, 11, 15], "model__weights": ["uniform", "distance"], "model__p": [1, 2]}}
                            inner_groups = pd.Series(groups[tr]).nunique()
                            inner_splits = min(3, int(inner_groups))
                            if inner_splits < 2:
                                raise ValueError("At least two training groups are required for inner hyperparameter tuning.")
                            inner_cv = GroupKFold(n_splits=inner_splits)
                            method = str(tuning_method).lower()
                            if method == "random":
                                search = RandomizedSearchCV(pipe, spaces[name], n_iter=max(1, int(tuning_iter)),
                                    scoring="neg_root_mean_squared_error", cv=inner_cv,
                                    random_state=int(random_state)+fold, n_jobs=1, refit=True, error_score="raise")
                                search.fit(X.iloc[tr], y[tr], groups=groups[tr])
                                pipe = search.best_estimator_
                                best_params = search.best_params_
                            elif method == "grid":
                                search = GridSearchCV(pipe, spaces[name], scoring="neg_root_mean_squared_error",
                                    cv=inner_cv, n_jobs=1, refit=True, error_score="raise")
                                search.fit(X.iloc[tr], y[tr], groups=groups[tr])
                                pipe = search.best_estimator_
                                best_params = search.best_params_
                            elif method == "bayesian":
                                try:
                                    import optuna
                                except ImportError as exc:
                                    raise ImportError("Bayesian optimisation requires the optional dependency optuna. Install with: pip install optuna") from exc
                                def objective(trial):
                                    if name in ("Random Forest", "Extra Trees"):
                                        params = {"model__n_estimators": trial.suggest_int("n_estimators",150,600,step=150), "model__max_depth": trial.suggest_categorical("max_depth",[None,5,10,20]), "model__min_samples_leaf": trial.suggest_int("min_samples_leaf",1,8), "model__max_features": trial.suggest_categorical("max_features",[1.0,"sqrt",0.7])}
                                    elif name == "HistGradientBoosting":
                                        params = {"model__learning_rate": trial.suggest_float("learning_rate",0.02,0.25,log=True), "model__max_iter": trial.suggest_categorical("max_iter",[100,200,400]), "model__max_leaf_nodes": trial.suggest_categorical("max_leaf_nodes",[15,31,63]), "model__l2_regularization": trial.suggest_float("l2_regularization",0.0,2.0)}
                                    elif name == "SVR":
                                        params = {"model__C": trial.suggest_float("C",0.05,100.0,log=True), "model__epsilon": trial.suggest_float("epsilon",0.005,0.5,log=True), "model__kernel": trial.suggest_categorical("kernel",["rbf","linear"]), "model__gamma": trial.suggest_categorical("gamma",["scale","auto"])}
                                    else:
                                        params = {"model__n_neighbors": trial.suggest_int("n_neighbors",3,15,step=2), "model__weights": trial.suggest_categorical("weights",["uniform","distance"]), "model__p": trial.suggest_int("p",1,2)}
                                    candidate = clone(pipe).set_params(**params)
                                    scores = cross_val_score(candidate, X.iloc[tr], y[tr], groups=groups[tr], cv=inner_cv, scoring="neg_root_mean_squared_error", n_jobs=1)
                                    return float(-np.mean(scores))
                                study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=int(random_state)+fold))
                                study.optimize(objective, n_trials=max(2,int(tuning_iter)), show_progress_bar=False)
                                best_params = {}
                                for k,v in study.best_params.items(): best_params["model__"+k] = v
                                pipe = clone(pipe).set_params(**best_params)
                                pipe.fit(X.iloc[tr], y[tr])
                            else:
                                raise ValueError("tuning_method must be random, grid or bayesian")
                            tuned_parameters.setdefault(name, []).append(best_params)
                        else:
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
                                cov_struct={"exchangeable": sm.cov_struct.Exchangeable(), "independence": sm.cov_struct.Independence()}[str(conventional_parameters.get("gee_covariance", "exchangeable"))]).fit()
                        else:
                            fit = None
                            model_fit = smf.mixedlm(formula, data=train, groups=train[group_col])
                            fit_error = None
                            for optimizer in ("lbfgs", "powell", "cg"):
                                try:
                                    candidate = model_fit.fit(reml=bool(conventional_parameters.get("mixed_reml", False)), method=optimizer, disp=False)
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
                "status": "completed", "warnings": "", "tuned_parameters": str(tuned_parameters.get(name, []))})
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
            "tuned_parameters": tuned_parameters,
            "interpretation": "Predictive comparison only. It does not compare causal estimands, coefficient inference, or biological mechanisms. Group bootstrap intervals quantify uncertainty under the supplied independent grouping unit."}
