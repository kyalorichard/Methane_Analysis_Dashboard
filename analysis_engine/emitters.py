
import numpy as np
import pandas as pd
from analysis_engine.emitter_thresholds import assign_emitter_tails

def build_emitter_cohorts(df, phenotype, tail_percent=10, animal_id_col=None,
                          aggregation="median", min_records=1):
    """Create mutually exclusive low/high tail cohorts from an animal-level phenotype.

    Repeated observations are collapsed per animal before percentile thresholds are
    calculated. If no animal ID is available, each row is treated as an observational
    unit and this limitation must be disclosed.
    """
    if phenotype not in df.columns:
        raise KeyError(f"Phenotype '{phenotype}' is not in the dataset.")
    if not 0 < float(tail_percent) <= 25:
        raise ValueError("tail_percent must be >0 and <=25.")
    d = df.copy()
    d["_phenotype_value"] = pd.to_numeric(d[phenotype], errors="coerce")
    d = d.loc[d["_phenotype_value"].notna()].copy()
    if d.empty:
        raise ValueError("No valid numeric observations are available for this phenotype.")

    has_animal_id = bool(animal_id_col and animal_id_col in d.columns and d[animal_id_col].notna().any())
    unit_col = animal_id_col if has_animal_id else None
    if has_animal_id:
        d = d.loc[d[unit_col].notna()].copy()
        numeric = d.select_dtypes(include="number").columns.tolist()
        # Avoid aggregating the derived phenotype twice.
        agg = "median" if aggregation == "median" else "mean"
        grouped = d.groupby(unit_col, dropna=True)
        out = grouped[numeric].agg(agg)
        # Retain representative categorical metadata (mode; deterministic first on ties).
        for col in d.columns:
            if col in numeric or col in [unit_col, "_phenotype_value"]:
                continue
            out[col] = grouped[col].agg(lambda x: x.mode(dropna=True).iloc[0] if not x.mode(dropna=True).empty else pd.NA)
        out[phenotype] = grouped["_phenotype_value"].agg(agg)
        out["n_measurements"] = grouped.size()
        out = out.loc[out["n_measurements"] >= int(min_records)].reset_index()
        unit_label = "animal"
    else:
        out = d.drop(columns=["_phenotype_value"]).copy()
        out["n_measurements"] = 1
        unit_label = "record (animal ID unavailable)"

    values = pd.to_numeric(out[phenotype], errors="coerce").dropna()
    if values.empty:
        raise ValueError("No analysis units remain after applying the minimum-record requirement.")
    # Shared rank-based tail assignment is also used by round-specific tracking.
    out = out.loc[pd.to_numeric(out[phenotype], errors="coerce").notna()].copy()
    labels, percentiles, low_cut, high_cut = assign_emitter_tails(out[phenotype], tail_percent)
    out["emitter_group"] = labels
    out["phenotype_percentile"] = percentiles
    out["phenotype_used"] = phenotype
    out["low_threshold_value"] = low_cut
    out["high_threshold_value"] = high_cut
    out["tail_percent"] = float(tail_percent)
    return out, {
        "unit": unit_label, "n_units": int(len(out)),
        "n_low": int((out.emitter_group == "Low emitter").sum()),
        "n_high": int((out.emitter_group == "High emitter").sum()),
        "n_intermediate": int((out.emitter_group == "Intermediate").sum()),
        "low_cutpoint": low_cut, "high_cutpoint": high_cut,
        "tail_percent": float(tail_percent), "phenotype": phenotype,
        "aggregation": aggregation if has_animal_id else "not applicable",
        "animal_level": bool(has_animal_id)
    }

def emitter_group_summary(cohorts, phenotype):
    d = cohorts.loc[cohorts["emitter_group"].isin(["Low emitter", "High emitter"])].copy()
    return (d.groupby("emitter_group")[phenotype]
            .agg(n="count", mean="mean", sd="std", median="median",
                 q1=lambda x: x.quantile(.25), q3=lambda x: x.quantile(.75),
                 minimum="min", maximum="max").reset_index())

def emitter_profile(cohorts, group_col="emitter_group"):
    """Summarise numeric and categorical variables by emitter group."""
    d = cohorts.loc[cohorts[group_col].isin(["Low emitter", "High emitter"])].copy()
    numeric = [c for c in d.select_dtypes(include="number").columns
               if c not in ["phenotype_percentile", "tail_percent", "low_threshold_value", "high_threshold_value"]]
    rows = []
    for col in numeric:
        for group, part in d.groupby(group_col):
            x = pd.to_numeric(part[col], errors="coerce").dropna()
            rows.append({"variable": col, "variable_type": "numeric", "emitter_group": group,
                         "n": len(x), "mean": x.mean(), "sd": x.std(),
                         "median": x.median(), "q1": x.quantile(.25), "q3": x.quantile(.75)})
    categorical = [c for c in d.select_dtypes(include=["object", "category", "string"]).columns
                   if c not in [group_col, "phenotype_used"]]
    for col in categorical:
        for group, part in d.groupby(group_col):
            counts = part[col].fillna("Missing").astype(str).value_counts(normalize=True) * 100
            for category, pct in counts.items():
                rows.append({"variable": col, "variable_type": "categorical_percent",
                             "emitter_group": group, "category": category, "percent": pct,
                             "n": int((part[col].fillna("Missing").astype(str) == category).sum())})
    return pd.DataFrame(rows)
