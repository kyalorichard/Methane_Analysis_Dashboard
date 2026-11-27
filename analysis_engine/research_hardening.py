"""Research-grade grouped classification, mixed models and configurable QC."""
from __future__ import annotations
import numpy as np
import pandas as pd
import warnings
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler, LabelEncoder
from sklearn.model_selection import StratifiedGroupKFold, GroupKFold
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
    precision_score, recall_score, roc_auc_score, average_precision_score,
    confusion_matrix)
from sklearn.base import clone

CLASSIFIERS = {
    "Logistic Regression": LogisticRegression(max_iter=3000, class_weight="balanced"),
    "Random Forest": RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1),
    "Extra Trees": ExtraTreesClassifier(n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1),
    "HistGradientBoosting": HistGradientBoostingClassifier(random_state=42)
}

def grouped_classification_benchmark(df, outcome, features, animal_id, selected_models=None, n_splits=5, seed=42):
    """Out-of-fold classification metrics with all records from an animal in one fold."""
    if outcome not in df or animal_id not in df:
        raise ValueError("Outcome and animal identifier must exist in the dataset.")
    features=[c for c in features if c in df.columns and c not in {outcome, animal_id}]
    if not features: raise ValueError("Select at least one predictor.")
    d=df[[outcome,animal_id]+features].dropna(subset=[outcome,animal_id]).copy()
    if d[animal_id].nunique()<3: raise ValueError("At least three unique animals are required.")
    # Drop rows whose class cannot be represented and encode labels consistently.
    enc=LabelEncoder(); y=enc.fit_transform(d[outcome].astype(str))
    counts=pd.Series(y).value_counts()
    if len(counts)<2: raise ValueError("The target must contain at least two classes.")
    groups=d[animal_id].astype(str).to_numpy()
    n_splits=min(int(n_splits), d[animal_id].nunique())
    # Stratified group folds are preferred; reduce folds until every train fold has all classes.
    splitter=StratifiedGroupKFold(n_splits=n_splits,shuffle=True,random_state=seed)
    numeric=[c for c in features if pd.api.types.is_numeric_dtype(d[c])]
    categorical=[c for c in features if c not in numeric]
    prep=ColumnTransformer([
        ("num",Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler())]),numeric),
        ("cat",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore"))]),categorical)
    ])
    names=list(CLASSIFIERS) if selected_models is None else list(selected_models)
    unknown=sorted(set(names)-set(CLASSIFIERS))
    if unknown: raise ValueError(f"Unknown classifier(s): {unknown}")
    rows=[]; matrices={}
    splits=list(splitter.split(d[features],y,groups))
    for name in names:
        pred=np.full(len(d),-1,dtype=int); prob_parts=[]; valid=True; errors=[]
        for train_idx,test_idx in splits:
            if len(np.unique(y[train_idx]))<2:
                valid=False; errors.append("A training fold contains fewer than two classes."); break
            pipe=Pipeline([("prep",clone(prep)),("model",clone(CLASSIFIERS[name]))])
            try:
                pipe.fit(d.iloc[train_idx][features],y[train_idx]); pred[test_idx]=pipe.predict(d.iloc[test_idx][features])
            except Exception as exc:
                valid=False; errors.append(str(exc)[:180]); break
        if not valid or (pred<0).any():
            rows.append({"model":name,"error":"; ".join(errors) or "Incomplete out-of-fold predictions"}); continue
        row={"model":name,"n_animals":int(d[animal_id].nunique()),"n_records":len(d),
             "n_classes":len(enc.classes_),"accuracy":accuracy_score(y,pred),
             "balanced_accuracy":balanced_accuracy_score(y,pred),
             "macro_f1":f1_score(y,pred,average="macro",zero_division=0),
             "weighted_f1":f1_score(y,pred,average="weighted",zero_division=0),
             "macro_precision":precision_score(y,pred,average="macro",zero_division=0),
             "macro_recall":recall_score(y,pred,average="macro",zero_division=0)}
        # AUC requires aligned probabilities and every class represented in every test fold.
        row["roc_auc_ovr"] = np.nan
        matrices[name]=pd.DataFrame(confusion_matrix(y,pred,labels=np.arange(len(enc.classes_))),index=enc.classes_,columns=enc.classes_)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("macro_f1",ascending=False,na_position="last"), matrices, list(map(str,enc.classes_))


def fit_mixed_effects(df, outcome, animal_id, fixed_effects=None, session_col=None, reml=True):
    """Compatibility adapter to the canonical mixed-model service.

    Retains the historical ``(estimates, summary)`` return contract.
    """
    from analysis_engine.mixed_models import fit_animal_random_intercept
    fit, used, summary = fit_animal_random_intercept(
        df, outcome, animal_id, fixed_effects=fixed_effects,
        session_col=session_col, reml=reml, min_records=2
    )
    ci = fit.conf_int()
    estimates = pd.DataFrame({
        "term": fit.params.index, "estimate": fit.params.values,
        "std_error": fit.bse.reindex(fit.params.index).values,
        "z_value": fit.tvalues.reindex(fit.params.index).values,
        "p_value": fit.pvalues.reindex(fit.params.index).values,
        "ci_lower": ci.iloc[:, 0].reindex(fit.params.index).values,
        "ci_upper": ci.iloc[:, 1].reindex(fit.params.index).values,
    })
    return estimates, summary


def configurable_qc(df, rules=None):
    """Backward-compatible adapter to the canonical configured-range QC service."""
    from analysis_engine.quality_control import configured_range_summary
    return configured_range_summary(df, rules)
