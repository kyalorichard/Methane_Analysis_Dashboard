"""Canonical conventional statistical model adapters."""
import pandas as pd
import statsmodels.formula.api as smf


def _formula(df, outcome, predictors):
    terms=[f'C(Q("{x}"))' if df[x].dtype=='object' or str(df[x].dtype).startswith('category') else f'Q("{x}")' for x in predictors]
    return f'Q("{outcome}") ~ ' + (' + '.join(terms) if terms else '1')


def fit_ols(df, outcome, predictors, settings=None):
    cfg=(settings or {}).get('statistics', {})
    d=df[[outcome]+predictors].dropna().copy()
    if len(d)<max(10,len(predictors)+3): raise ValueError('Insufficient complete observations for this model.')
    alpha=float(cfg.get('alpha',.05))
    return smf.ols(_formula(d,outcome,predictors),data=d).fit(cov_type='HC3').get_robustcov_results()


def fit_gee(df, outcome, predictors, animal_id, settings=None):
    import statsmodels.api as sm
    cfg=(settings or {}).get('conventional', {})
    d=df[[outcome]+predictors+[animal_id]].dropna().copy()
    covariance=str(cfg.get('gee_covariance','exchangeable')).lower()
    cov_map={'exchangeable':sm.cov_struct.Exchangeable,'independence':sm.cov_struct.Independence,'ar1':sm.cov_struct.Autoregressive,'nested':sm.cov_struct.Nested}
    if covariance not in cov_map: raise ValueError(f'Unsupported GEE covariance structure: {covariance}')
    return smf.gee(_formula(d,outcome,predictors),groups=d[animal_id],data=d,cov_struct=cov_map[covariance]()).fit()


def fit_mixedlm(df, outcome, predictors, animal_id, settings=None):
    cfg=(settings or {}).get('conventional', {})
    d=df[[outcome]+predictors+[animal_id]].dropna().copy()
    return smf.mixedlm(_formula(d,outcome,predictors),data=d,groups=d[animal_id]).fit(reml=bool(cfg.get('mixed_reml',True)),method='lbfgs',disp=False)
