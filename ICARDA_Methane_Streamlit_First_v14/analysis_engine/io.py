"""Dataset ingestion: CSV/Parquet/Excel input, pandas DataFrame output."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import pandas as pd

ALIASES = {
 "animal_id":["animalid","animal_id","animal","id","tag","tag_id"],
 "species":["species","livestock_species"], "breed":["breed","genotype","type"],
 "sex":["sex","gender"], "weight":["weight","body_weight","bw","liveweight"],
 "round":["round","visit","session","sampling_round"],
 "date":["date","file_date","measurement_date","sample_date","recording_date"],
 "recording_duration":["recording_duration","duration","duration_sec","recording_time"],
 "member":["member","cbbp","program_status","group"],
 "methane":["mean_methane","methane","ch4","ch4_concentration","methane_concentration"],
}
SUPPORTED_EXTENSIONS={".csv",".parquet",".pq",".xlsx",".xls"}

def load_uploaded_data(upload):
    """Load CSV, Parquet/PQ or Excel upload as a pandas DataFrame."""
    name=str(getattr(upload,"name","uploaded_dataset.csv"))
    ext=Path(name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported format {ext or 'unknown'}. Upload CSV, Parquet (.parquet/.pq), or Excel (.xlsx/.xls).")
    payload=upload.getvalue() if hasattr(upload,"getvalue") else upload.read()
    buf=BytesIO(payload)
    if ext==".csv":
        try: df=pd.read_csv(buf)
        except UnicodeDecodeError:
            buf.seek(0); df=pd.read_csv(buf,encoding="latin-1")
    elif ext in {".parquet",".pq"}: df=pd.read_parquet(buf,engine="pyarrow")
    else: df=pd.read_excel(buf)
    if not isinstance(df,pd.DataFrame): raise TypeError("Uploaded file did not produce a tabular dataset.")
    return df

def dataframe_to_parquet_bytes(df,compression="snappy"):
    """Return canonical Parquet bytes; index is excluded from scientific data."""
    if not isinstance(df,pd.DataFrame): raise TypeError("Expected a pandas DataFrame.")
    if df.columns.duplicated().any(): raise ValueError("Cannot store a dataset with duplicate column names.")
    buf=BytesIO(); df.to_parquet(buf,engine="pyarrow",compression=compression,index=False)
    return buf.getvalue()

def infer_roles(df):
    norm={str(c).strip().lower().replace(" ","_"):c for c in df.columns}
    return {role:next((norm[a] for a in aliases if a in norm),None) for role,aliases in ALIASES.items()}

def validate_dataset(df):
    issues=[]
    if df.empty: issues.append("The uploaded dataset has no rows.")
    if df.columns.duplicated().any(): issues.append("Duplicate column names detected.")
    if len(df.columns)<2: issues.append("At least two columns are expected.")
    if df.isna().all(axis=1).any(): issues.append(f"{int(df.isna().all(axis=1).sum())} fully empty rows detected.")
    roles=infer_roles(df)
    if not roles["animal_id"]: issues.append("Animal identifier was not automatically detected. Map it before repeated-measures or grouped ML analyses.")
    if not roles["methane"]: issues.append("No methane outcome was automatically detected. Select or map the appropriate phenotype.")
    return issues
