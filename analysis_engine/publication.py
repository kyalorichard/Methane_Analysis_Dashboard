'''Publication-oriented, reproducible outputs for methane phenotype studies.'''
from __future__ import annotations
from datetime import datetime, timezone
from io import BytesIO
import json, platform, zipfile
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
from analysis_engine.data_provenance import dataframe_fingerprint

def _safe_json(value):
    if isinstance(value, dict): return {str(k): _safe_json(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [_safe_json(v) for v in value]
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,float)): return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)): return bool(value)
    if isinstance(value, pd.Timestamp): return value.isoformat()
    return value

def publication_tables(df, outcome, animal_id=None, group_col=None, covariates=None):
    if df.empty: raise ValueError("Cannot generate a report from an empty dataset.")
    if outcome not in df: raise ValueError(f"Outcome '{outcome}' is not present.")
    y=pd.to_numeric(df[outcome],errors="coerce")
    if y.notna().sum()<3: raise ValueError("At least three numeric outcome observations are required.")
    covariates=covariates or []
    desc=df.describe(include="all").transpose().reset_index().rename(columns={"index":"variable"})
    summary=pd.DataFrame([{"outcome":outcome,"n":int(y.notna().sum()),"missing_n":int(y.isna().sum()),
        "mean":y.mean(),"sd":y.std(),"median":y.median(),"q1":y.quantile(.25),"q3":y.quantile(.75),
        "minimum":y.min(),"maximum":y.max(),"skewness":y.skew(),"kurtosis":y.kurt()}])
    analysis=df.copy()
    unit="record"
    if animal_id and animal_id in df:
        analysis=df.dropna(subset=[animal_id]).groupby(animal_id,as_index=False).agg({
            c:("median" if pd.api.types.is_numeric_dtype(df[c]) else "first")
            for c in df.columns if c!=animal_id})
        unit="animal (numeric variables aggregated by median; categorical variables by first observed value)"
    group_table=pd.DataFrame()
    if group_col and group_col in analysis:
        tmp=analysis[[group_col,outcome]].copy()
        tmp[outcome]=pd.to_numeric(tmp[outcome],errors="coerce")
        group_table=(tmp.dropna().groupby(group_col)[outcome].agg(n="count",mean="mean",sd="std",
            median="median",q1=lambda x:x.quantile(.25),q3=lambda x:x.quantile(.75),
            minimum="min",maximum="max").reset_index())
    corr_cols=[c for c in [outcome]+covariates if c in analysis and pd.api.types.is_numeric_dtype(analysis[c])]
    corr=analysis[corr_cols].corr(method="spearman").reset_index().rename(columns={"index":"variable"}) if len(corr_cols)>1 else pd.DataFrame()
    return {"descriptive_statistics":desc,"outcome_summary":summary,"group_summary":group_table,
        "spearman_correlations":corr,"analysis_unit":unit,"analysis_n":len(analysis)}

def build_publication_bundle(df, *, outcome, animal_id=None, group_col=None, covariates=None,
    dataset_name="active_dataset", study_title="Methane phenotype analysis",
    study_species="Not specified", protocol_notes=""):
    tables=publication_tables(df,outcome,animal_id,group_col,covariates)
    y=pd.to_numeric(df[outcome],errors="coerce").dropna()
    figs={}
    fig=px.histogram(y,nbins=30,labels={"value":outcome,"count":"Records"},title=f"Distribution of {outcome}")
    fig.update_layout(template="plotly_white",font=dict(family="Arial",size=13))
    figs["outcome_distribution.html"]=pio.to_html(fig,full_html=True,include_plotlyjs="cdn")
    if group_col and group_col in df:
        p=df[[group_col,outcome]].copy(); p[outcome]=pd.to_numeric(p[outcome],errors="coerce"); p=p.dropna()
        if not p.empty:
            box=px.box(p,x=group_col,y=outcome,points="outliers",title=f"{outcome} by {group_col}")
            box.update_layout(template="plotly_white",font=dict(family="Arial",size=13))
            figs["outcome_by_group.html"]=pio.to_html(box,full_html=True,include_plotlyjs="cdn")
    fingerprint=dataframe_fingerprint(df)
    limitations=[
        "This bundle is descriptive and does not by itself establish causal effects.",
        "Repeated records are aggregated to animal-level medians for independent-unit group summaries.",
        "Concentration and AUC measurements are not methane mass flux (e.g. g/day) without validated calibration.",
        "Distribution summaries do not replace residual diagnostics or model-specific assumption checks.",
        "Thresholds and phenotype definitions must be justified by the study protocol and instrument validation."
    ]
    manifest={"report_generated_utc":datetime.now(timezone.utc).isoformat(),"study_title":study_title,
        "dataset_name":dataset_name,"species":study_species,"outcome":outcome,"animal_id":animal_id,
        "group_variable":group_col,"covariates":covariates or [],"source_rows":int(len(df)),
        "source_columns":int(df.shape[1]),"analysis_unit":tables["analysis_unit"],
        "analysis_n":tables["analysis_n"],"dataset_fingerprint_sha256":fingerprint,
        "python_version":platform.python_version(),"pandas_version":pd.__version__,"limitations":limitations}
    methods=f'''# Methods and reporting notes

**Study:** {study_title}  
**Dataset:** {dataset_name}  
**Species:** {study_species}  
**Source observations:** {len(df):,}  
**Outcome:** `{outcome}`  
**Animal identifier:** `{animal_id or "Not specified"}`  
**Grouping variable:** `{group_col or "Not specified"}`

## Statistical approach
Outcome-specific summaries use numeric observations and report sample size, missingness, mean, standard deviation, median, interquartile range, minimum and maximum. Where an animal identifier is supplied, repeated observations are collapsed to animal-level medians for independent-unit group summaries and rank-based correlations. Categorical fields use the first observed value per animal. Spearman correlations are descriptive associations, not causal estimates.

## Interpretation and limitations
{chr(10).join("- "+x for x in limitations)}

## Protocol notes
{protocol_notes or "Add instrument calibration, recording protocol, phenotype definitions, units, inclusion criteria and quality-control thresholds before manuscript submission."}

## Reproducibility
The ZIP contains tables, interactive figures, a JSON manifest with a dataset fingerprint, and a starter Python script. The fingerprint identifies dataframe content and row order; it is not a substitute for archiving source data under appropriate governance.
'''
    buf=BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("README_REPORT.md",methods)
        z.writestr("manifest.json",json.dumps(_safe_json(manifest),indent=2))
        for name,frame in tables.items():
            if isinstance(frame,pd.DataFrame): z.writestr(f"tables/{name}.csv",frame.to_csv(index=False))
        excel=BytesIO()
        with pd.ExcelWriter(excel,engine="openpyxl") as writer:
            for name,frame in tables.items():
                if isinstance(frame,pd.DataFrame): frame.to_excel(writer,sheet_name=name[:31],index=False)
        z.writestr("tables/publication_tables.xlsx",excel.getvalue())
        for name,html in figs.items(): z.writestr(f"figures/{name}",html)
        starter=f'''# Recreate core descriptive tables from the original CSV.
# Usage: python reproduce_report.py source.csv output_directory
import sys
from pathlib import Path
import pandas as pd
from analysis_engine.publication import publication_tables
source=Path(sys.argv[1]); output=Path(sys.argv[2]); output.mkdir(parents=True,exist_ok=True)
data=pd.read_csv(source)
tables=publication_tables(data, outcome={outcome!r}, animal_id={animal_id!r}, group_col={group_col!r})
for name, frame in tables.items():
    if isinstance(frame,pd.DataFrame): frame.to_csv(output/f"{{name}}.csv",index=False)
'''
        z.writestr("reproducibility/reproduce_report.py",starter)
    return buf.getvalue()
