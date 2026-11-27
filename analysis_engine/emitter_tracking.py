
"""Longitudinal emitter classification and transition summaries."""
import numpy as np
import pandas as pd
from analysis_engine.emitter_thresholds import assign_emitter_tails

def classify_emitters_by_round(df, animal_col, round_col, phenotype, tail_percent=10,
                              aggregation="median", min_records=1):
    required = [animal_col, round_col, phenotype]
    missing = [c for c in required if c not in df.columns]
    if missing: raise ValueError(f"Missing required columns: {missing}")
    if not 0 < float(tail_percent) <= 25: raise ValueError("tail_percent must be >0 and <=25.")
    d = df[required].copy()
    round_order = list(pd.unique(d[round_col].dropna()))
    d[phenotype] = pd.to_numeric(d[phenotype], errors="coerce")
    d = d.dropna(subset=required)
    if d.empty: raise ValueError("No valid animal-round phenotype records.")
    agg = "median" if aggregation == "median" else "mean"
    unit = d.groupby([animal_col, round_col], as_index=False).agg(
        **{phenotype:(phenotype, agg), "n_measurements":(phenotype,"count")}
    )
    unit = unit[unit.n_measurements >= int(min_records)].copy()
    if unit.empty: raise ValueError("No animal-round units remain after minimum-record filtering.")
    unit["emitter_group"] = "Intermediate"
    unit["phenotype_percentile"] = np.nan
    thresholds = []
    for rnd, idx in unit.groupby(round_col, sort=False).groups.items():
        vals = unit.loc[idx, phenotype]
        labels, percentiles, low_cut, high_cut = assign_emitter_tails(vals, tail_percent)
        unit.loc[idx, "emitter_group"] = labels
        unit.loc[idx, "phenotype_percentile"] = percentiles
        thresholds.append({"round":rnd,"n_animals":len(vals),"low_cutpoint":low_cut,
                           "high_cutpoint":high_cut,"n_low":int((unit.loc[idx,"emitter_group"]=="Low emitter").sum()),
                           "n_high":int((unit.loc[idx,"emitter_group"]=="High emitter").sum())})
    unit["phenotype"] = phenotype
    unit["tail_percent"] = float(tail_percent)
    order_map = {value: i for i, value in enumerate(round_order)}
    unit["_round_order"] = unit[round_col].map(order_map)
    unit = unit.sort_values([animal_col, "_round_order"]).drop(columns="_round_order").reset_index(drop=True)
    return unit, pd.DataFrame(thresholds)

def emitter_persistence_summary(assignments, animal_col, round_col):
    if assignments.empty: return pd.DataFrame(), pd.DataFrame()
    pivot = assignments.pivot_table(index=animal_col, columns=round_col,
                                    values="emitter_group", aggfunc="first")
    ordered_rounds = list(dict.fromkeys(assignments[round_col].tolist()))
    pivot = pivot.reindex(columns=ordered_rounds)
    transition_rows=[]
    for a,b in zip(ordered_rounds[:-1], ordered_rounds[1:]):
        pair = pivot[[a,b]].dropna()
        if pair.empty: continue
        matrix = pd.crosstab(pair[a], pair[b], normalize="index")*100
        matrix = matrix.reindex(index=["Low emitter","Intermediate","High emitter"],
                                columns=["Low emitter","Intermediate","High emitter"], fill_value=0)
        for from_group in matrix.index:
            for to_group in matrix.columns:
                transition_rows.append({"from_round":a,"to_round":b,"from_group":from_group,
                                         "to_group":to_group,"percent_within_origin_group":matrix.loc[from_group,to_group],
                                         "n_animals":int((pair[a]==from_group).sum())})
    transitions = pd.DataFrame(transition_rows)
    observed = pivot.dropna(axis=1, how="all")
    if observed.shape[1] >= 2:
        all_rounds_present = observed.notna().all(axis=1)
        consistent = observed.loc[all_rounds_present]
        persistence = pd.DataFrame([
            {"classification":"Consistently high", "n_animals":int((consistent=="High emitter").all(axis=1).sum())},
            {"classification":"Consistently low", "n_animals":int((consistent=="Low emitter").all(axis=1).sum())},
            {"classification":"Never high or low (intermediate only)", "n_animals":int((consistent=="Intermediate").all(axis=1).sum())},
            {"classification":"Changed at least once", "n_animals":int((consistent.nunique(axis=1)>1).sum())},
            {"classification":"Animals observed in every round", "n_animals":int(len(consistent))}
        ])
    else:
        persistence = pd.DataFrame([{"classification":"At least two rounds are required","n_animals":0}])
    return transitions, persistence
