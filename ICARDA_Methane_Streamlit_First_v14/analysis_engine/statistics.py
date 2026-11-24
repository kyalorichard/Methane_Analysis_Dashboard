import pandas as pd
import statsmodels.formula.api as smf
def fit_ols(df,outcome,predictors):
    cols=[outcome]+predictors
    d=df[cols].dropna().copy()
    if len(d)<max(10,len(predictors)+3): raise ValueError("Insufficient complete observations for this model.")
    formula=f'Q("{outcome}") ~ '+" + ".join(f'C(Q("{x}"))' if d[x].dtype=="object" else f'Q("{x}")' for x in predictors)
    return smf.ols(formula,data=d).fit(cov_type="HC3")
def fit_gee(df,outcome,predictors,animal_id):
    import statsmodels.api as sm
    cols=[outcome]+predictors+[animal_id]
    d=df[cols].dropna().copy()
    formula=f'Q("{outcome}") ~ '+" + ".join(f'C(Q("{x}"))' if d[x].dtype=="object" else f'Q("{x}")' for x in predictors)
    return smf.gee(formula,groups=d[animal_id],data=d,cov_struct=sm.cov_struct.Exchangeable()).fit()
def fit_mixedlm(df,outcome,predictors,animal_id):
    cols=[outcome]+predictors+[animal_id]
    d=df[cols].dropna().copy()
    formula=f'Q("{outcome}") ~ '+" + ".join(f'C(Q("{x}"))' if d[x].dtype=="object" else f'Q("{x}")' for x in predictors) if predictors else f'Q("{outcome}") ~ 1'
    return smf.mixedlm(formula,data=d,groups=d[animal_id]).fit(reml=True,method="lbfgs",disp=False)
