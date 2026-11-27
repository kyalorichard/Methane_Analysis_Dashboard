"""Shared percentile-tail assignment for static and longitudinal emitter workflows."""
from __future__ import annotations
import numpy as np
import pandas as pd


def assign_emitter_tails(values: pd.Series, tail_percent: float = 10.0):
    """Return low/intermediate/high labels, percentile ranks and empirical cutpoints.

    Rank-based assignment targets approximate tail sizes while quantile cutpoints
    are retained as descriptive thresholds. Ties at a cutpoint are not treated
    as proof of biological emitter status.
    """
    p = float(tail_percent) / 100.0
    if not 0 < p <= 0.25:
        raise ValueError("tail_percent must be >0 and <=25.")
    x = pd.to_numeric(values, errors="coerce")
    valid = x.replace([np.inf, -np.inf], np.nan).dropna()
    if valid.empty:
        raise ValueError("No valid numeric phenotype values are available for tail assignment.")
    low_cut = float(valid.quantile(p))
    high_cut = float(valid.quantile(1 - p))
    ranks = x.rank(method="first", pct=True)
    labels = pd.Series("Intermediate", index=x.index, dtype="object")
    labels.loc[ranks <= p] = "Low emitter"
    labels.loc[ranks > 1 - p] = "High emitter"
    percentiles = x.rank(method="average", pct=True) * 100.0
    return labels, percentiles, low_cut, high_cut
