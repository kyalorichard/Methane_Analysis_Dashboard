import pandas as pd
def dataset_profile(df):
    return {"n_records":int(len(df)),"n_variables":int(df.shape[1]),
            "missing_percent":float(df.isna().mean().mean()*100),
            "duplicate_rows":int(df.duplicated().sum())}
def descriptive_table(df, columns):
    x=df[columns].apply(pd.to_numeric,errors="coerce")
    out=x.describe(percentiles=[.25,.5,.75]).T.reset_index(names="variable")
    out["missing_n"]=x.isna().sum().values
    return out
