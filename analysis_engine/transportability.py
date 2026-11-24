"""External-cohort audit, distribution shift and cluster-bootstrap benchmarking.

These diagnostics support (but do not certify) transportability. Cohort independence,
measurement harmonisation and the independent sampling unit must be established by study design.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def audit_external_cohort(development: pd.DataFrame, external: pd.DataFrame, *,
                          animal_id: str | None = None, group_id: str | None = None,
                          cohort_id: str | None = None, required_columns=None) -> dict:
    """Audit schema and identifier overlap; never infer independence from filenames."""
    if not isinstance(development, pd.DataFrame) or not isinstance(external, pd.DataFrame):
        raise TypeError("Development and external inputs must be pandas DataFrames.")
    required = list(required_columns or [])
    missing_dev = sorted(set(required) - set(development.columns))
    missing_ext = sorted(set(required) - set(external.columns))
    identifiers = {}
    for label, col in (("animal", animal_id), ("group", group_id), ("cohort", cohort_id)):
        if col:
            if col not in development or col not in external:
                identifiers[label] = {"column": col, "status": "MISSING"}
            else:
                a = set(development[col].dropna().astype(str))
                b = set(external[col].dropna().astype(str))
                overlap = sorted(a & b)
                identifiers[label] = {"column": col, "development_unique": len(a),
                    "external_unique": len(b), "overlap_count": len(overlap),
                    "overlap_examples": overlap[:10],
                    "status": "OVERLAP" if overlap else "NO_OBSERVED_OVERLAP"}
    overlaps = [k for k,v in identifiers.items() if v.get("status") == "OVERLAP"]
    missing_ids = [k for k,v in identifiers.items() if v.get("status") == "MISSING"]
    warnings=[]
    if overlaps: warnings.append("Identifier overlap detected; external independence is not established.")
    if missing_ids: warnings.append("One or more requested identifier columns are missing.")
    if not any(k in identifiers for k in ("animal", "group", "cohort")):
        warnings.append("No identifiers were supplied; cohort independence cannot be audited computationally.")
    if missing_dev or missing_ext: warnings.append("Required variables are missing; harmonise schema before model evaluation.")
    return {"development_records":len(development),"external_records":len(external),
        "required_columns":required,"missing_from_development":missing_dev,"missing_from_external":missing_ext,
        "identifier_audit":identifiers,"independence_screen_passed":not overlaps and not missing_ids and not missing_dev and not missing_ext,
        "warnings":warnings,
        "interpretation":"No observed identifier overlap is a screening result, not proof of independent sampling, temporal separation or measurement comparability. Verify cohort provenance, SOPs, instruments, units and calibration metadata."}


def distribution_shift_report(development: pd.DataFrame, external: pd.DataFrame,
                              features, *, numeric_bins=10) -> pd.DataFrame:
    """Numeric standardized mean differences and categorical prevalence shifts.

    Numeric SMD uses pooled SD. Categorical output is the maximum absolute category
    prevalence difference. Missingness shift is reported separately for each feature.
    """
    rows=[]
    for col in features:
        if col not in development or col not in external:
            rows.append({"feature":col,"feature_type":"unknown","status":"MISSING_COLUMN"}); continue
        a,b=development[col],external[col]
        miss_a=float(a.isna().mean()); miss_b=float(b.isna().mean())
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            x=pd.to_numeric(a,errors="coerce").dropna().to_numpy(float)
            y=pd.to_numeric(b,errors="coerce").dropna().to_numpy(float)
            if len(x) and len(y):
                pooled=np.sqrt((np.var(x,ddof=1)*(len(x)-1)+np.var(y,ddof=1)*(len(y)-1))/max(len(x)+len(y)-2,1)) if len(x)>1 and len(y)>1 else np.nan
                smd=(float(np.mean(y)-np.mean(x))/pooled) if np.isfinite(pooled) and pooled>0 else np.nan
                rows.append({"feature":col,"feature_type":"numeric","development_mean":float(np.mean(x)),"external_mean":float(np.mean(y)),"standardized_mean_difference":smd,"max_category_prevalence_difference":np.nan,"development_missing_fraction":miss_a,"external_missing_fraction":miss_b,"missingness_difference":miss_b-miss_a,"status":"OK"})
            else: rows.append({"feature":col,"feature_type":"numeric","status":"NO_NONMISSING_VALUES"})
        else:
            pa=a.astype("string").fillna("<MISSING>").value_counts(normalize=True)
            pb=b.astype("string").fillna("<MISSING>").value_counts(normalize=True)
            cats=pa.index.union(pb.index)
            diff=float((pb.reindex(cats,fill_value=0)-pa.reindex(cats,fill_value=0)).abs().max()) if len(cats) else np.nan
            rows.append({"feature":col,"feature_type":"categorical","standardized_mean_difference":np.nan,"max_category_prevalence_difference":diff,"development_missing_fraction":miss_a,"external_missing_fraction":miss_b,"missingness_difference":miss_b-miss_a,"status":"OK"})
    return pd.DataFrame(rows)


def cluster_bootstrap_regression(y_true, y_pred, groups, *, n_boot=1000,
                                 confidence=.95, random_state=42) -> dict:
    """Cluster bootstrap CIs for regression metrics; resamples independent groups."""
    y=np.asarray(y_true,dtype=float); p=np.asarray(y_pred,dtype=float); g=np.asarray(groups)
    if not (len(y)==len(p)==len(g)): raise ValueError("y_true, y_pred and groups must have equal lengths.")
    ok=np.isfinite(y)&np.isfinite(p)&pd.notna(g); y,p,g=y[ok],p[ok],g[ok]
    unique=pd.unique(g)
    if len(unique)<5: raise ValueError("At least five independent clusters are required.")
    if n_boot<200: raise ValueError("Use at least 200 bootstrap replicates.")
    if not .80<=confidence<=.99: raise ValueError("confidence must be between 0.80 and 0.99.")
    idx_by={v:np.flatnonzero(g==v) for v in unique}; rng=np.random.default_rng(random_state)
    def metrics(ix):
        yy,pp=y[ix],p[ix]
        return [mean_absolute_error(yy,pp),np.sqrt(mean_squared_error(yy,pp)),r2_score(yy,pp) if len(yy)>1 and np.var(yy)>0 else np.nan,float(np.mean(yy-pp))]
    point=metrics(np.arange(len(y))); draws=[]
    for _ in range(int(n_boot)):
        chosen=rng.choice(unique,size=len(unique),replace=True)
        ix=np.concatenate([idx_by[v] for v in chosen])
        draws.append(metrics(ix))
    arr=np.asarray(draws,float); alpha=1-confidence
    names=["mae","rmse","r2","mean_error_observed_minus_predicted"]
    return {"n_records":len(y),"n_clusters":len(unique),"n_bootstrap":int(n_boot),"confidence":confidence,
        "metrics":{name:{"estimate":float(point[i]),"ci_low":float(np.nanquantile(arr[:,i],alpha/2)),"ci_high":float(np.nanquantile(arr[:,i],1-alpha/2))} for i,name in enumerate(names)},
        "resampling_unit":"independent cluster","warning":"Use the highest independent sampling unit (e.g. farm/herd/site), not animal, when animals are nested within clusters."}


def paired_model_comparison(y_true, predictions: dict, groups, *, n_boot=1000,
                            confidence=.95, random_state=42) -> pd.DataFrame:
    """Paired cluster-bootstrap RMSE/MAE differences on identical held-out records.

    Differences are model minus reference; negative values favour the candidate.
    """
    y=np.asarray(y_true,dtype=float); g=np.asarray(groups)
    if len(y)!=len(g): raise ValueError("Outcome and groups must have equal lengths.")
    if len(predictions)<2: raise ValueError("Supply at least two model prediction vectors.")
    pred={k:np.asarray(v,dtype=float) for k,v in predictions.items()}
    if any(len(v)!=len(y) for v in pred.values()): raise ValueError("All models must predict the same held-out records.")
    if any(not np.isfinite(v).all() for v in pred.values()) or not np.isfinite(y).all(): raise ValueError("Predictions and outcomes must be finite.")
    unique=pd.unique(g)
    if len(unique)<5: raise ValueError("At least five independent clusters are required.")
    idx_by={v:np.flatnonzero(g==v) for v in unique}; rng=np.random.default_rng(random_state)
    names=list(pred); ref=names[0]; rows=[]
    for name in names[1:]:
        def score(ix, model, metric):
            return mean_squared_error(y[ix],pred[model][ix])**.5 if metric=="rmse" else mean_absolute_error(y[ix],pred[model][ix])
        for metric in ("rmse","mae"):
            point=score(np.arange(len(y)),name,metric)-score(np.arange(len(y)),ref,metric); vals=[]
            for _ in range(int(n_boot)):
                chosen=rng.choice(unique,size=len(unique),replace=True); ix=np.concatenate([idx_by[v] for v in chosen])
                vals.append(score(ix,name,metric)-score(ix,ref,metric))
            alpha=1-confidence
            rows.append({"reference_model":ref,"candidate_model":name,"metric":metric,"difference_candidate_minus_reference":float(point),"ci_low":float(np.quantile(vals,alpha/2)),"ci_high":float(np.quantile(vals,1-alpha/2)),"n_clusters":len(unique)})
    return pd.DataFrame(rows)
