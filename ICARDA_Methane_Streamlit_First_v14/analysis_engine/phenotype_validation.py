"""Exploratory, auditable diagnostics for derived and source phenotypes.

This module reports statistical evidence; it does not certify biological validity.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats


def distribution_diagnostics(df: pd.DataFrame, phenotype: str) -> dict:
    x = pd.to_numeric(df[phenotype], errors='coerce')
    v = x.dropna().to_numpy(float)
    if len(v) == 0:
        raise ValueError('The selected phenotype has no valid numeric observations.')
    q1, med, q3 = np.quantile(v, [.25, .5, .75])
    iqr = q3 - q1
    outlier = (v < q1 - 1.5 * iqr) | (v > q3 + 1.5 * iqr) if iqr > 0 else np.zeros(len(v), bool)
    mean = float(np.mean(v)); sd = float(np.std(v, ddof=1)) if len(v) > 1 else np.nan
    return {
        'n_total': int(len(x)), 'n_valid': int(len(v)), 'n_missing': int(x.isna().sum()),
        'missing_pct': float(x.isna().mean() * 100), 'mean': mean, 'sd': sd,
        'cv_pct': float(sd / abs(mean) * 100) if np.isfinite(sd) and mean != 0 else np.nan,
        'min': float(np.min(v)), 'p01': float(np.quantile(v, .01)), 'p05': float(np.quantile(v, .05)),
        'q1': float(q1), 'median': float(med), 'q3': float(q3),
        'p95': float(np.quantile(v, .95)), 'p99': float(np.quantile(v, .99)), 'max': float(np.max(v)),
        'skewness': float(stats.skew(v, bias=False)) if len(v) >= 3 and np.std(v) > 0 else np.nan,
        'kurtosis_excess': float(stats.kurtosis(v, bias=False)) if len(v) >= 4 and np.std(v) > 0 else np.nan,
        'iqr_outlier_n': int(outlier.sum()), 'iqr_outlier_pct': float(outlier.mean() * 100),
        'unique_values': int(pd.Series(v).nunique()),
    }


def group_profile(df: pd.DataFrame, phenotype: str, group: str) -> pd.DataFrame:
    d = df[[phenotype, group]].copy()
    d[phenotype] = pd.to_numeric(d[phenotype], errors='coerce')
    d = d.dropna(subset=[phenotype, group])
    if d.empty:
        return pd.DataFrame()
    return d.groupby(group, dropna=False)[phenotype].agg(n='count', mean='mean', sd='std', median='median', q1=lambda x: x.quantile(.25), q3=lambda x: x.quantile(.75)).reset_index()


def repeated_measure_diagnostics(df: pd.DataFrame, animal_col: str, phenotype: str, session_col: str | None = None, min_pairs: int = 3):
    from .advanced import repeatability_icc
    d = df[[animal_col, phenotype] + ([session_col] if session_col else [])].copy()
    d[phenotype] = pd.to_numeric(d[phenotype], errors='coerce')
    d = d.dropna(subset=[animal_col, phenotype])
    counts = d.groupby(animal_col)[phenotype].size()
    paired_ids = counts[counts >= 2].index
    paired = d[d[animal_col].isin(paired_ids)]
    result = {'n_animals': int(d[animal_col].nunique()), 'n_animals_repeated': int(len(paired_ids)), 'n_records': int(len(d))}
    if len(paired_ids) >= 3:
        try:
            result.update(repeatability_icc(d, animal_col, phenotype))
        except Exception as exc:
            result['icc_error'] = str(exc)
    else:
        result['icc_error'] = 'At least three animals with repeated records are required.'
    session_summary = pd.DataFrame()
    paired_wide = pd.DataFrame()
    if session_col and session_col in d.columns:
        session_summary = d.groupby(session_col)[phenotype].agg(n='count', mean='mean', sd='std', median='median').reset_index()
        # Aggregate within animal/session first, then compare the first two sessions in sorted order.
        w = d.groupby([animal_col, session_col])[phenotype].mean().unstack(session_col)
        if w.shape[1] >= 2:
            a, b = list(w.columns[:2])
            z = w[[a, b]].dropna()
            if len(z) >= min_pairs:
                diff = z[b] - z[a]
                session_result = {'session_a': str(a), 'session_b': str(b), 'n_paired_animals': int(len(z)),
                                  'mean_change_b_minus_a': float(diff.mean()), 'sd_change': float(diff.std(ddof=1)),
                                  'median_change': float(diff.median()),
                                  'pearson_r': float(stats.pearsonr(z[a], z[b]).statistic) if z[a].nunique()>1 and z[b].nunique()>1 else np.nan,
                                  'spearman_rho': float(stats.spearmanr(z[a], z[b]).statistic) if z[a].nunique()>1 and z[b].nunique()>1 else np.nan}
                paired_wide = z.reset_index()
                result['paired_session_comparison'] = session_result
    return result, session_summary, paired_wide


def correlate_with_covariate(df: pd.DataFrame, phenotype: str, covariate: str, animal_col: str | None = None):
    d = df[[phenotype, covariate] + ([animal_col] if animal_col and animal_col in df else [])].copy()
    d[phenotype] = pd.to_numeric(d[phenotype], errors='coerce')
    d[covariate] = pd.to_numeric(d[covariate], errors='coerce')
    d = d.dropna(subset=[phenotype, covariate])
    if animal_col and animal_col in d:
        d = d.groupby(animal_col, as_index=False)[[phenotype, covariate]].median()
    if len(d) < 4:
        raise ValueError('At least four complete independent units are required.')
    pearson = stats.pearsonr(d[phenotype], d[covariate]) if d[phenotype].nunique()>1 and d[covariate].nunique()>1 else None
    spearman = stats.spearmanr(d[phenotype], d[covariate]) if d[phenotype].nunique()>1 and d[covariate].nunique()>1 else None
    return {'n_units': int(len(d)), 'pearson_r': float(pearson.statistic) if pearson else np.nan,
            'pearson_p': float(pearson.pvalue) if pearson else np.nan,
            'spearman_rho': float(spearman.statistic) if spearman else np.nan,
            'spearman_p': float(spearman.pvalue) if spearman else np.nan}, d
