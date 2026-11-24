
import numpy as np
import pandas as pd

SHEEP_NOTEBOOK_EXPECTED = [
"AnimalID","Sex","Breed","weight","Round","log_day","Description","Member",
"Diurnality","feedtime","Assessor","file_date","recording_duration","n_peaks",
"n_resp","n_eruct","mean_methane","mean_resp","mean_eruct","max_resp",
"max_eruct","peak_duration_sec","eruct_per_min","AUC_peaks","AUC_peaks_3min",
"AUC_peak_per_sec","n_records","full_duration_sec","AUC_full","AUC_3min","AUC_per_sec"
]
CANDIDATE_PHENOTYPES = [
"mean_methane","mean_resp","mean_eruct","max_resp","max_eruct",
"eruct_per_min","AUC_peaks","AUC_peaks_3min","AUC_peak_per_sec",
"AUC_full","AUC_3min","AUC_per_sec","methane_rate_from_auc",
"peak_rate_per_min","resp_rate_per_min","eruct_rate_per_min_recalc"
]
def clean_sheep_notebook_schema(df):
    """Apply the notebook's non-destructive text/date harmonisation and QC flags."""
    d=df.copy()
    for c in d.select_dtypes(include="object").columns:
        d[c]=d[c].astype("string").str.strip().str.replace(r"\s+"," ",regex=True)
    if "file_date" in d: d["file_date"]=pd.to_datetime(d["file_date"],errors="coerce")
    for c in d.columns:
        if c not in ["AnimalID","Sex","Breed","Round","Description","Member","Diurnality","feedtime","Assessor","file_date"]:
            d[c]=pd.to_numeric(d[c],errors="ignore")
    if "Round" in d:
        d["Round"]=d["Round"].replace({"Round 1":"R1","Round 2":"R2","1":"R1","2":"R2"})
    if "Member" in d:
        d["Member"]=d["Member"].astype("string").str.upper().replace({"NON CBBP":"NON-CBBP","NONCBBP":"NON-CBBP"})
    for c in ["Sex"]:
        if c in d: d[c]=d[c].astype("string").str.upper()
    for c in ["Breed","Description"]:
        if c in d: d[c]=d[c].astype("string").str.title()
    return d
def derive_duration_normalised_phenotypes(df):
    d=df.copy()
    if {"AUC_full","full_duration_sec"}.issubset(d.columns):
        d["methane_rate_from_auc"]=pd.to_numeric(d["AUC_full"],errors="coerce")/pd.to_numeric(d["full_duration_sec"],errors="coerce").replace(0,np.nan)
        d["auc_full_per_min"]=pd.to_numeric(d["AUC_full"],errors="coerce")/(pd.to_numeric(d["full_duration_sec"],errors="coerce")/60).replace(0,np.nan)
    duration=pd.to_numeric(d["full_duration_sec"],errors="coerce") if "full_duration_sec" in d else None
    if duration is not None:
        for source,target in [("n_peaks","peak_rate_per_min"),("n_resp","resp_rate_per_min"),("n_eruct","eruct_rate_per_min_recalc")]:
            if source in d:
                d[target]=pd.to_numeric(d[source],errors="coerce")/(duration/60).replace(0,np.nan)
    return d
def notebook_qc_flags(df):
    d=df
    q=pd.DataFrame(index=d.index)
    if "AnimalID" in d: q["missing_animal_id"]=d["AnimalID"].isna()
    if "file_date" in d: q["missing_date"]=d["file_date"].isna()
    if "weight" in d: q["nonpositive_weight"]=pd.to_numeric(d["weight"],errors="coerce").le(0)
    if "full_duration_sec" in d: q["nonpositive_duration"]=pd.to_numeric(d["full_duration_sec"],errors="coerce").le(0)
    count_cols=[c for c in ["n_peaks","n_resp","n_eruct","n_records"] if c in d]
    if count_cols: q["negative_counts"]=d[count_cols].apply(pd.to_numeric,errors="coerce").lt(0).any(axis=1)
    auc_cols=[c for c in ["AUC_peaks","AUC_peaks_3min","AUC_full","AUC_3min"] if c in d]
    if auc_cols: q["negative_auc"]=d[auc_cols].apply(pd.to_numeric,errors="coerce").lt(0).any(axis=1)
    if "log_day" in d: q["log_day_outside_1_3"]=~pd.to_numeric(d["log_day"],errors="coerce").isin([1,2,3])
    if "full_duration_sec" in d: q["duration_over_3min"]=pd.to_numeric(d["full_duration_sec"],errors="coerce").gt(180)
    return q
