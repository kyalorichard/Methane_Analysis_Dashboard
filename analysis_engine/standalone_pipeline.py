"""Integrated, reproducible analysis pipeline for livestock methane phenotypes.

The pipeline produces auditable descriptive, quality-control, repeatability,
group-comparison, association and optional animal-grouped ML outputs.
It deliberately avoids treating uncalibrated sensor signals as methane mass flux.
"""
from __future__ import annotations
from datetime import datetime, timezone
from io import BytesIO
import json, platform, zipfile, importlib.metadata, os
import numpy as np
import pandas as pd
from .metrics import descriptive_table
from .phenotype_validation import distribution_diagnostics, repeated_measure_diagnostics, group_profile, correlate_with_covariate
from .advanced import group_comparison
from .ml import grouped_regression_benchmark
from .data_provenance import dataframe_fingerprint


def _json_safe(obj):
    if isinstance(obj, dict): return {str(k):_json_safe(v) for k,v in obj.items()}
    if isinstance(obj, (list,tuple)): return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,float)):
        return float(obj) if np.isfinite(obj) else None
    if isinstance(obj, (np.bool_,)): return bool(obj)
    if isinstance(obj, (pd.Timestamp,)): return obj.isoformat()
    return obj


def dataset_audit(df: pd.DataFrame, animal_id: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if df.empty: raise ValueError("The active dataset is empty.")
    if df.columns.duplicated().any(): raise ValueError("Duplicate column names must be resolved before analysis.")
    n=len(df)
    rows=[]
    for c in df.columns:
        s=df[c]
        rows.append({
            "variable":str(c), "dtype":str(s.dtype), "non_missing_n":int(s.notna().sum()),
            "missing_n":int(s.isna().sum()), "missing_percent":float(s.isna().mean()*100),
            "unique_n":int(s.nunique(dropna=True)), "constant":bool(s.nunique(dropna=True)<=1),
            "example_values":" | ".join(map(str,s.dropna().astype(str).unique()[:4]))
        })
    dictionary=pd.DataFrame(rows).sort_values(["missing_percent","variable"],ascending=[False,True])
    issue_rows=[]
    duplicates=int(df.duplicated().sum())
    issue_rows.append({"check":"Exact duplicate rows","status":"PASS" if duplicates==0 else "REVIEW","value":duplicates,"interpretation":"No exact duplicate rows." if duplicates==0 else "Review duplicate records before deciding whether they are valid repeat measurements."})
    empty_rows=int(df.isna().all(axis=1).sum())
    issue_rows.append({"check":"Fully empty rows","status":"PASS" if empty_rows==0 else "REVIEW","value":empty_rows,"interpretation":"No fully empty rows." if empty_rows==0 else "Remove fully empty rows after confirming source integrity."})
    issue_rows.append({"check":"Missing cells","status":"PASS" if df.isna().mean().mean()<.05 else "REVIEW","value":round(float(df.isna().mean().mean()*100),2),"interpretation":"Overall missingness percentage; inspect variable-level missingness."})
    if animal_id and animal_id in df:
        issue_rows.append({"check":"Animal identifier","status":"PASS" if df[animal_id].notna().all() else "REVIEW","value":int(df[animal_id].nunique()),"interpretation":"Unique animals; missing identifiers prevent grouped validation for those records."})
    else:
        issue_rows.append({"check":"Animal identifier","status":"BLOCKED","value":"Not mapped","interpretation":"Map a stable animal identifier before repeated-measures inference or predictive validation."})
    audit={"n_records":int(n),"n_variables":int(df.shape[1]),"duplicate_rows":duplicates,
           "fully_empty_rows":empty_rows,"missing_percent":float(df.isna().mean().mean()*100),
           "n_animals":int(df[animal_id].nunique()) if animal_id and animal_id in df else None,
           "data_sha256":dataframe_fingerprint(df)}
    return dictionary,pd.DataFrame(issue_rows),audit


def run_integrated_analysis(df: pd.DataFrame, *, dataset_name="active_dataset", species="other",
                            outcome: str, animal_id: str | None, session_col: str | None = None,
                            group_col: str | None = None, covariates: list[str] | None = None,
                            ml_features: list[str] | None = None, ml_models: list[str] | None = None,
                            run_ml: bool = False, seed: int = 42) -> dict:
    if outcome not in df.columns: raise ValueError(f"Outcome '{outcome}' is not in the dataset.")
    y=pd.to_numeric(df[outcome],errors="coerce")
    if y.notna().sum()<5: raise ValueError("The selected outcome must have at least five valid numeric observations.")
    covariates=covariates or []
    dictionary,qc,audit=dataset_audit(df,animal_id)
    desc=descriptive_table(df,[c for c in df.select_dtypes(include="number").columns])
    phenotype=distribution_diagnostics(df,outcome)
    outputs={"data_dictionary":dictionary,"quality_control":qc,"descriptive_statistics":desc}
    summaries={"dataset":audit,"outcome":outcome,"phenotype_distribution":phenotype}
    # Animal-level analysis frame: repeated records are collapsed by median for independent-unit analyses.
    independent=df.copy()
    if animal_id and animal_id in df.columns:
        independent=df.groupby(animal_id,dropna=True).agg({
            c:("median" if pd.api.types.is_numeric_dtype(df[c]) else "first")
            for c in df.columns if c != animal_id
        }).reset_index()
        summaries["independent_unit"]="animal-level median for numeric variables; first observed value for categorical variables"
        summaries["n_independent_animals"]=int(independent[animal_id].nunique())
    else:
        summaries["independent_unit"]="record-level; independence cannot be guaranteed"
        summaries["n_independent_animals"]=None
    if animal_id and animal_id in df.columns:
        if session_col and session_col in df.columns:
            rep,session_summary,paired=repeated_measure_diagnostics(df,animal_id,outcome,session_col)
        else:
            rep,session_summary,paired=repeated_measure_diagnostics(df,animal_id,outcome)
        summaries["repeatability"]=rep
        outputs["session_summary"]=session_summary
        outputs["paired_session_data"]=paired
    # Group profiles and independent-unit tests
    if group_col and group_col in independent.columns and group_col != outcome:
        gp=group_profile(independent,outcome,group_col)
        outputs["group_profile"]=gp
        if independent[group_col].nunique(dropna=True)>=2:
            try: summaries["group_test"]=group_comparison(independent,outcome,group_col,method="auto")
            except Exception as exc: summaries["group_test_error"]=str(exc)
    # Correlations use one row per animal when a stable ID is available.
    corr_rows=[]
    for c in (covariates or []):
        if c not in independent.columns or c==outcome: continue
        try:
            result,_=correlate_with_covariate(independent,outcome,c,None)
            corr_rows.append({"covariate":c,**result})
        except Exception as exc:
            corr_rows.append({"covariate":c,"error":str(exc)})
    outputs["associations"]=pd.DataFrame(corr_rows)
    # Optional grouped ML. Explicitly exclude ID and outcome from predictors.
    if run_ml:
        if not animal_id or animal_id not in df.columns:
            summaries["ml_status"]="Not run: map a stable animal ID to enable animal-grouped validation."
        elif not ml_features:
            summaries["ml_status"]="Not run: select at least one predictor."
        else:
            feats=[c for c in ml_features if c in df.columns and c not in {outcome,animal_id}]
            try:
                ml=grouped_regression_benchmark(df,outcome,feats,animal_id,selected_models=ml_models or None)
                outputs["ml_benchmark"]=ml
                summaries["ml_status"]="Completed using GroupKFold with animals kept together."
                summaries["ml_validation"]="GroupKFold by animal; preprocessing fitted within each fold."
            except Exception as exc:
                summaries["ml_status"]=f"Could not complete: {exc}"
    else:
        summaries["ml_status"]="Not requested."
    summaries["scientific_caveats"]=[
        "Methane concentration and AUC are instrument-derived signals, not methane mass flux unless supported by validated calibration.",
        "Animal-level aggregation supports independent-unit summaries but can discard within-animal temporal information.",
        "Simple group tests and correlations are descriptive/inferential at the animal level and do not establish causality.",
        "Repeatability estimates are not heritability; choose the ICC model to match the measurement design.",
        "Predictive validation is grouped by animal to reduce repeated-record leakage.",
        "Clustering and phenotype classes require stability and external biological validation before biological interpretation."
    ]
    package_versions = {}
    for package in ("numpy", "scipy", "pandas", "scikit-learn", "statsmodels", "plotly", "pyarrow"):
        try: package_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: package_versions[package] = None
    manifest={
        "run_timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "dataset_name":dataset_name,"species":species,"outcome":outcome,
        "animal_id":animal_id,"session_col":session_col,"group_col":group_col,
        "covariates":covariates,"ml_features":ml_features or [],
        "ml_models":ml_models or [],"run_ml":run_ml,"random_seed":seed,
        "python_version":platform.python_version(),"pandas_version":pd.__version__,
        "package_versions":package_versions,"application_version":os.getenv("APP_VERSION") or os.getenv("GIT_COMMIT") or "unknown",
        "audit":audit,"analysis_scope":"integrated exploratory and inferential analysis"
    }
    return {"tables":outputs,"summary":summaries,"manifest":manifest}


def build_analysis_bundle(result: dict, dataset: pd.DataFrame | None = None) -> bytes:
    """Create a portable ZIP containing CSV tables, Excel workbook, JSON manifest and HTML summary."""
    files={}
    tables=result["tables"]
    excel=BytesIO()
    with pd.ExcelWriter(excel,engine="openpyxl") as writer:
        for name,table in tables.items():
            if isinstance(table,pd.DataFrame) and not table.empty:
                table.to_excel(writer,sheet_name=name[:31],index=False)
    files["analysis_results.xlsx"]=excel.getvalue()
    for name,table in tables.items():
        if isinstance(table,pd.DataFrame):
            files[f"tables/{name}.csv"]=table.to_csv(index=False).encode("utf-8")
    files["manifest.json"]=json.dumps(_json_safe(result["manifest"]),indent=2).encode()
    files["summary.json"]=json.dumps(_json_safe(result["summary"]),indent=2).encode()
    if dataset is not None:
        files["data/analysis_dataset.csv"]=dataset.to_csv(index=False).encode("utf-8")
    summary=_json_safe(result["summary"])
    rows=[]
    for key,value in summary.items():
        if isinstance(value,(dict,list)):
            value=json.dumps(value,indent=2,ensure_ascii=False)
        rows.append(f"<tr><th>{key}</th><td><pre>{str(value)}</pre></td></tr>")
    html="""<!doctype html><html><head><meta charset='utf-8'><title>Methane phenotype analysis report</title>
    <style>body{font-family:Arial,sans-serif;color:#183247;margin:36px;line-height:1.5}h1{color:#176B5B}
    table{border-collapse:collapse;width:100%}th,td{border:1px solid #dce7e1;padding:10px;text-align:left;vertical-align:top}
    th{background:#edf5f0;width:25%}pre{white-space:pre-wrap;font-family:Consolas,monospace}</style></head>
    <body><h1>Livestock Methane Phenotype Analysis</h1><p>Integrated analysis summary. See the accompanying workbook and CSV tables for detailed outputs.</p>
    <table>"""+''.join(rows)+"""</table><h2>Interpretation and limitations</h2><ul>"""+''.join(f"<li>{x}</li>" for x in summary.get("scientific_caveats",[]))+"""</ul></body></html>"""
    files["report.html"]=html.encode("utf-8")
    bundle=BytesIO()
    with zipfile.ZipFile(bundle,"w",zipfile.ZIP_DEFLATED) as z:
        for name,content in files.items(): z.writestr(name,content)
    return bundle.getvalue()
