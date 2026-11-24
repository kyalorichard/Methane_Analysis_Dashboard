"""Leakage-aware classification validation, calibration and external assessment."""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler, LabelEncoder
from sklearn.model_selection import StratifiedGroupKFold, GroupKFold, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
    precision_score, recall_score, roc_auc_score, average_precision_score,
    brier_score_loss, log_loss, confusion_matrix)
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.svm import SVC

CLASSIFICATION_GRIDS = {
    "Logistic Regression": (LogisticRegression(max_iter=4000, class_weight="balanced"),
        {"model__C": [0.1, 1.0, 10.0]}),
    "Random Forest": (RandomForestClassifier(n_estimators=250, class_weight="balanced", random_state=42, n_jobs=-1),
        {"model__max_features": ["sqrt", 0.8], "model__min_samples_leaf": [1, 3]}),
    "Extra Trees": (ExtraTreesClassifier(n_estimators=250, class_weight="balanced", random_state=42, n_jobs=-1),
        {"model__max_features": ["sqrt", 0.8], "model__min_samples_leaf": [1, 3]}),
    "SVM": (SVC(class_weight="balanced", probability=True, random_state=42),
        {"model__C": [0.1, 1.0, 10.0], "model__kernel": ["rbf", "linear"]}),
}


def _prepare(df, outcome, group_col, features):
    if outcome not in df or group_col not in df:
        raise ValueError("Outcome and grouping identifier must exist.")
    features = [c for c in features if c in df and c not in {outcome, group_col}]
    if not features:
        raise ValueError("Select at least one predictor.")
    d = df[[outcome, group_col] + features].dropna(subset=[outcome, group_col]).copy()
    d[group_col] = d[group_col].astype(str)
    enc = LabelEncoder(); y = enc.fit_transform(d[outcome].astype(str))
    if len(enc.classes_) < 2:
        raise ValueError("Classification target must contain at least two classes.")
    if d[group_col].nunique() < 5:
        raise ValueError("At least five independent groups are required.")
    return d, features, y, enc


def _pipeline(d, features, estimator):
    numeric = [c for c in features if pd.api.types.is_numeric_dtype(d[c])]
    categorical = [c for c in features if c not in numeric]
    prep = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])
    return Pipeline([("prep", prep), ("model", clone(estimator))])


def _calibrate_probabilities(raw, y_cal, method):
    """Fit a multiclass logistic calibration map on inner OOF probabilities."""
    eps = 1e-7
    p = np.clip(np.asarray(raw, dtype=float), eps, 1-eps)
    p = p / p.sum(axis=1, keepdims=True)
    if method == "none":
        return None
    # Logistic calibration on log probabilities; fitted only on inner OOF predictions.
    calibrator = LogisticRegression(max_iter=3000, C=1e6)
    calibrator.fit(np.log(p), y_cal)
    return calibrator


def _apply_calibrator(calibrator, probabilities):
    if calibrator is None:
        p = np.clip(probabilities, 1e-7, 1)
        return p / p.sum(axis=1, keepdims=True)
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-7, 1)
    p = p / p.sum(axis=1, keepdims=True)
    out = calibrator.predict_proba(np.log(p))
    return out / out.sum(axis=1, keepdims=True)


def grouped_nested_classification(df, outcome, features, group_col, models=None,
                                  outer_splits=5, inner_splits=3, calibration="sigmoid",
                                  random_state=42, tune=True):
    """Nested grouped OOF classification with optional cross-fitted probability calibration.

    Hyperparameter selection and calibration are confined to each outer training fold.
    Group labels must represent the highest independent sampling unit.
    """
    d, features, y, enc = _prepare(df, outcome, group_col, features)
    groups = d[group_col].to_numpy(); n_groups = pd.Series(groups).nunique()
    outer_n = min(int(outer_splits), n_groups)
    if outer_n < 3: raise ValueError("At least three outer group folds are required.")
    names = list(CLASSIFICATION_GRIDS) if models is None else list(models)
    unknown = sorted(set(names)-set(CLASSIFICATION_GRIDS))
    if unknown: raise ValueError(f"Unknown classifier(s): {unknown}")
    if calibration not in {"sigmoid", "none"}: raise ValueError("Calibration must be 'sigmoid' or 'none'.")
    outer = StratifiedGroupKFold(n_splits=outer_n, shuffle=True, random_state=random_state)
    all_results = {}; summary_rows=[]
    for name in names:
        base, grid = CLASSIFICATION_GRIDS[name]
        oof_prob = np.full((len(d), len(enc.classes_)), np.nan)
        fold_info=[]; failures=[]
        for fold, (tr, te) in enumerate(outer.split(d[features], y, groups), 1):
            if len(np.unique(y[tr])) != len(enc.classes_):
                failures.append(f"Outer fold {fold}: training partition lacks one or more classes."); continue
            estimator = clone(base)
            if tune:
                inner_group_n = pd.Series(groups[tr]).nunique()
                inner_n = min(int(inner_splits), inner_group_n)
                if inner_n < 2:
                    failures.append(f"Outer fold {fold}: insufficient groups for inner tuning."); continue
                search = GridSearchCV(_pipeline(d.iloc[tr], features, estimator), grid,
                    scoring="balanced_accuracy", cv=GroupKFold(n_splits=inner_n), n_jobs=-1,
                    refit=True, error_score="raise")
                try:
                    search.fit(d.iloc[tr][features], y[tr], groups=groups[tr])
                    fitted = search.best_estimator_; best_params = search.best_params_
                except Exception as exc:
                    failures.append(f"Outer fold {fold} tuning: {type(exc).__name__}: {str(exc)[:160]}"); continue
            else:
                fitted = _pipeline(d.iloc[tr], features, estimator)
                best_params = {}
            calibrator = None
            if calibration == "sigmoid":
                # Generate calibration training predictions from group-disjoint inner folds.
                inner_n = min(int(inner_splits), pd.Series(groups[tr]).nunique())
                inner = StratifiedGroupKFold(n_splits=inner_n, shuffle=True, random_state=random_state+fold)
                p_inner = np.full((len(tr), len(enc.classes_)), np.nan)
                try:
                    for itr, iva in inner.split(d.iloc[tr][features], y[tr], groups[tr]):
                        if len(np.unique(y[tr][itr])) != len(enc.classes_):
                            raise ValueError("Inner calibration training fold lacks a class.")
                        cal_model = clone(fitted)
                        cal_model.fit(d.iloc[tr].iloc[itr][features], y[tr][itr])
                        p_inner[iva] = cal_model.predict_proba(d.iloc[tr].iloc[iva][features])
                    if np.isnan(p_inner).any(): raise ValueError("Incomplete inner OOF probabilities.")
                    calibrator = _calibrate_probabilities(p_inner, y[tr], "sigmoid")
                except Exception as exc:
                    failures.append(f"Outer fold {fold} calibration: {type(exc).__name__}: {str(exc)[:160]}")
                    continue
            try:
                fitted.fit(d.iloc[tr][features], y[tr])
                p = fitted.predict_proba(d.iloc[te][features])
                oof_prob[te] = _apply_calibrator(calibrator, p)
                fold_info.append({"fold": fold, "train_groups": int(pd.Series(groups[tr]).nunique()),
                    "test_groups": int(pd.Series(groups[te]).nunique()), "best_params": best_params})
            except Exception as exc:
                failures.append(f"Outer fold {fold} prediction: {type(exc).__name__}: {str(exc)[:160]}")
        valid = np.isfinite(oof_prob).all(axis=1)
        if not valid.all():
            summary_rows.append({"model":name,"records_with_oof_probabilities":int(valid.sum()),
                "records_total":len(d),"status":"INCOMPLETE","warnings":" | ".join(failures)})
            continue
        pred = oof_prob.argmax(axis=1)
        row = {"model":name,"status":"COMPLETE","n_groups":int(n_groups),"n_records":len(d),
            "outer_folds_completed":len(fold_info),"accuracy":accuracy_score(y,pred),
            "balanced_accuracy":balanced_accuracy_score(y,pred),
            "macro_f1":f1_score(y,pred,average="macro",zero_division=0),
            "weighted_f1":f1_score(y,pred,average="weighted",zero_division=0),
            "macro_precision":precision_score(y,pred,average="macro",zero_division=0),
            "macro_recall":recall_score(y,pred,average="macro",zero_division=0),
            "log_loss":log_loss(y,oof_prob,labels=np.arange(len(enc.classes_))),
            "multiclass_brier":float(np.mean(np.sum((oof_prob-np.eye(len(enc.classes_))[y])**2,axis=1))),
            "roc_auc_ovr":(roc_auc_score(y,oof_prob[:,1]) if len(enc.classes_)==2 else roc_auc_score(y,oof_prob,multi_class="ovr",average="macro")),
            "calibration_method":calibration,"warnings":" | ".join(failures)}
        cm = pd.DataFrame(confusion_matrix(y,pred,labels=np.arange(len(enc.classes_))),index=enc.classes_,columns=enc.classes_)
        prob_df = pd.DataFrame(oof_prob,columns=[f"probability_{c}" for c in enc.classes_])
        prob_df.insert(0,"observed_class",[enc.classes_[i] for i in y]); prob_df.insert(0,group_col,groups)
        all_results[name]={"summary":row,"probabilities":prob_df,"confusion_matrix":cm,"folds":fold_info}
        summary_rows.append(row)
    return pd.DataFrame(summary_rows).sort_values("macro_f1",ascending=False,na_position="last"), all_results, list(map(str,enc.classes_))


def external_classification_validation(estimator, external_df, outcome, features, group_col=None):
    """Evaluate a frozen fitted classifier on an independent external cohort; never refits."""
    missing=[c for c in [outcome]+list(features) if c not in external_df]
    if missing: raise ValueError(f"External dataset is missing required columns: {missing}")
    d=external_df[[outcome]+list(features)+([group_col] if group_col else [])].dropna(subset=[outcome]).copy()
    y_true=d[outcome].astype(str).to_numpy()
    classes=np.asarray(estimator.classes_)
    if not set(np.unique(y_true)).issubset(set(classes.astype(str))):
        raise ValueError("External cohort contains outcome classes absent from the development model.")
    y_enc=np.array([list(classes.astype(str)).index(v) for v in y_true])
    p=estimator.predict_proba(d[features]); pred=p.argmax(axis=1)
    return {"n_records":len(d),"n_groups":int(d[group_col].nunique()) if group_col else None,
        "accuracy":float(accuracy_score(y_enc,pred)),"balanced_accuracy":float(balanced_accuracy_score(y_enc,pred)),
        "macro_f1":float(f1_score(y_enc,pred,average="macro",zero_division=0)),
        "log_loss":float(log_loss(y_enc,p,labels=np.arange(len(classes)))),
        "multiclass_brier":float(np.mean(np.sum((p-np.eye(len(classes))[y_enc])**2,axis=1))),
        "confusion_matrix":confusion_matrix(y_enc,pred,labels=np.arange(len(classes))).tolist(),
        "classes":classes.astype(str).tolist(),
        "warning":"Interpret as external validation only when cohort, animals and measurement process are independent and harmonised."}
