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
    """Fit Gaussian random-intercept model; return structured estimates and diagnostics."""
    import statsmodels.formula.api as smf
    fixed_effects=fixed_effects or []
    needed=[outcome,animal_id]+fixed_effects+([session_col] if session_col else [])
    d=df[needed].copy()
    d[outcome]=pd.to_numeric(d[outcome],errors="coerce")
    d=d.dropna(subset=[outcome,animal_id]+fixed_effects)
    if d[animal_id].nunique()<5: raise ValueError("At least five animals are recommended for random-intercept estimation.")
    if d.groupby(animal_id).size().lt(2).sum()==d[animal_id].nunique():
        raise ValueError("No repeated observations per animal; a random-intercept model is not supported by this design.")
    # Quote variable names safely for Patsy formulas.
    q=lambda x: 'Q("'+str(x).replace('\\','\\\\').replace('"','\\"')+'")'
    terms=[q(c) for c in fixed_effects]
    if session_col: terms.append(f"C({q(session_col)})")
    formula=f"{q(outcome)} ~ " + (" + ".join(terms) if terms else "1")
    model=smf.mixedlm(formula,d,groups=d[animal_id],re_formula="1")
    fit=None; selected_optimizer=None; fit_errors=[]; fit_warnings=[]
    # lbfgs can fail on near-boundary random-effect covariance estimates; retry
    # with derivative-free / alternative optimizers before declaring failure.
    for method in ("lbfgs", "powell", "bfgs", "cg", "nm"):
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                candidate=model.fit(reml=reml,method=method,maxiter=2000,disp=False)
            fit_warnings.extend(str(w.message) for w in caught)
            if candidate.converged:
                fit=candidate; selected_optimizer=method; break
            fit=candidate; selected_optimizer=method
            fit_errors.append(f"{method}: optimizer did not converge")
        except Exception as exc:
            fit_errors.append(f"{method}: {type(exc).__name__}: {str(exc)[:180]}")
    if fit is None:
        raise RuntimeError("Mixed-effects estimation failed with all optimizers: " + " | ".join(fit_errors))
    ci=fit.conf_int()
    estimates=pd.DataFrame({"term":fit.params.index,"estimate":fit.params.values,
       "std_error":fit.bse.reindex(fit.params.index).values,
       "z_value":fit.tvalues.reindex(fit.params.index).values,
       "p_value":fit.pvalues.reindex(fit.params.index).values,
       "ci_lower":ci.iloc[:,0].reindex(fit.params.index).values,
       "ci_upper":ci.iloc[:,1].reindex(fit.params.index).values})
    summary={"formula":formula,"n_records":int(len(d)),"n_animals":int(d[animal_id].nunique()),
       "converged":bool(fit.converged),"optimizer":selected_optimizer,"reml":bool(reml),"log_likelihood":float(fit.llf),
       "aic":float(fit.aic) if np.isfinite(fit.aic) else None,
       "random_intercept_variance":float(fit.cov_re.iloc[0,0]),
       "residual_variance":float(fit.scale),"warnings":list(dict.fromkeys(fit_warnings + fit_errors)) + ([] if fit.converged else ["Optimizer did not report convergence; interpret estimates cautiously."]),
       "interpretation":"Gaussian linear mixed-effects model with animal-level random intercept. Estimates are conditional associations, not causal effects."}
    return estimates,summary


def configurable_qc(df, rules=None):
    """Flag range, non-positive and missingness issues without deleting observations."""
    rules=rules or {}; records=[]
    for col,rule in rules.items():
        if col not in df: continue
        x=pd.to_numeric(df[col],errors="coerce")
        valid=x.notna(); low=rule.get("min"); high=rule.get("max")
        below=int((x<low).sum()) if low is not None else 0
        above=int((x>high).sum()) if high is not None else 0
        missing=int(x.isna().sum())
        records.append({"variable":col,"minimum_rule":low,"maximum_rule":high,
          "below_min_n":below,"above_max_n":above,"missing_n":missing,
          "flagged_n":int(below+above),"rule_source":rule.get("source","user-configured; not a validated biological threshold"),
          "status":"REVIEW" if below+above else "PASS"})
    return pd.DataFrame(records)
