"""Advanced, transparent statistical workflows for the Streamlit research platform.

These functions return estimates and diagnostics; they do not make biological
interpretations or certify a phenotype as valid without study-team review.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
import statsmodels.formula.api as smf

def _numeric_frame(df, cols):
    x=df[cols].copy()
    for c in cols: x[c]=pd.to_numeric(x[c],errors="coerce")
    return x

def bh_adjust(pvalues):
    p=np.asarray(pvalues,dtype=float)
    ok=np.isfinite(p)
    out=np.full(p.shape,np.nan)
    if ok.any(): out[ok]=multipletests(p[ok],method="fdr_bh")[1]
    return out

def repeatability_icc(df, animal_col, value_col, session_col=None, min_repeats=2):
    """Compatibility wrapper for the canonical unbalanced long-format ICC(1,1)."""
    from .reliability import estimate_long_format_icc1
    return estimate_long_format_icc1(df, animal_col, value_col, min_repeats=min_repeats)


def bootstrap_icc(df, animal_col, value_col, n_boot=500, seed=42):
    """Compatibility wrapper for the canonical subject-cluster ICC bootstrap."""
    from .reliability import bootstrap_long_format_icc1
    return bootstrap_long_format_icc1(df, animal_col, value_col, n_boot=n_boot, seed=seed)


def bland_altman(df, animal_col, value_col, session_col, session_a, session_b):
    """Compatibility wrapper; pairs subjects before using canonical agreement statistics."""
    from .reliability import bland_altman_long_format
    pairs, result = bland_altman_long_format(df, animal_col, value_col, session_col, session_a, session_b)
    return pairs.rename(columns={"difference_a_minus_b": "difference_b_minus_a"}).assign(
        difference_b_minus_a=lambda x: -x["difference_b_minus_a"]
    ), {
        "n_pairs": result["n_pairs"],
        "bias": -result["bias_first_minus_second"],
        "sd_difference": result["sd_of_differences"],
        "loa_lower": -result["upper_limit_of_agreement"],
        "loa_upper": -result["lower_limit_of_agreement"],
    }


def group_comparison(df, outcome, group, method="auto"):
    d=df[[outcome,group]].copy()
    d[outcome]=pd.to_numeric(d[outcome],errors="coerce")
    d=d.dropna()
    levels=list(d[group].dropna().unique())
    if len(levels)<2: raise ValueError("At least two non-empty groups are required.")
    arrays=[d.loc[d[group]==g,outcome].to_numpy(float) for g in levels]
    if any(len(a)<2 for a in arrays): raise ValueError("Each group needs at least two observations.")
    if method=="auto": method="kruskal" if len(levels)>2 else "welch"
    if method=="welch":
        if len(levels)!=2: raise ValueError("Welch t-test is for exactly two groups.")
        res=stats.ttest_ind(*arrays,equal_var=False)
        pooled=np.sqrt((arrays[0].var(ddof=1)+arrays[1].var(ddof=1))/2)
        effect=(arrays[1].mean()-arrays[0].mean())/pooled if pooled else np.nan
        return {"method":"Welch independent-samples t-test","statistic":float(res.statistic),"p_value":float(res.pvalue),
                "groups":levels,"n":[len(a) for a in arrays],"means":[float(a.mean()) for a in arrays],
                "mean_difference_group2_minus_group1":float(arrays[1].mean()-arrays[0].mean()),"cohen_d_approx":float(effect)}
    if method=="kruskal":
        res=stats.kruskal(*arrays)
        n=len(d); k=len(levels)
        eps=max(0.0,(res.statistic-k+1)/(n-k)) if n>k else np.nan
        pairs=[]
        for i in range(k):
            for j in range(i+1,k):
                r=stats.mannwhitneyu(arrays[i],arrays[j],alternative="two-sided")
                pairs.append({"group_1":str(levels[i]),"group_2":str(levels[j]),"p_value":float(r.pvalue)})
        if pairs:
            adj=bh_adjust([x["p_value"] for x in pairs])
            for x,q in zip(pairs,adj): x["p_fdr_bh"]=float(q)
        return {"method":"Kruskal-Wallis rank-sum test","statistic":float(res.statistic),"p_value":float(res.pvalue),
                "epsilon_squared":float(eps),"groups":[str(x) for x in levels],"n":[len(a) for a in arrays],
                "medians":[float(np.median(a)) for a in arrays],"pairwise_mann_whitney":pairs}
    raise ValueError("Unsupported comparison method.")

def fit_allometry(df, outcome, weight, covariates=None):
    covariates=covariates or []
    d=df[[outcome,weight]+covariates].copy()
    d[outcome]=pd.to_numeric(d[outcome],errors="coerce");d[weight]=pd.to_numeric(d[weight],errors="coerce")
    d=d[(d[outcome]>0)&(d[weight]>0)].dropna()
    if len(d)<10: raise ValueError("At least 10 positive complete observations are required.")
    formula=f'np.log(Q("{outcome}")) ~ np.log(Q("{weight}"))'
    for c in covariates: formula+=f' + C(Q("{c}"))' if d[c].dtype=="object" else f' + Q("{c}")'
    return smf.ols(formula,d).fit(cov_type="HC3")

def fit_quantile_regression(df,outcome,predictors,quantile=None,settings=None):
    cfg=(settings or {}).get("conventional", {})
    quantile=float(cfg.get("quantile", .5) if quantile is None else quantile)
    if not 0.05 <= quantile <= 0.95: raise ValueError("Quantile must be between 0.05 and 0.95.")
    d=df[[outcome]+predictors].copy()
    d[outcome]=pd.to_numeric(d[outcome],errors="coerce")
    d=d.dropna()
    if len(d)<max(20,4+len(predictors)): raise ValueError("Insufficient complete records for quantile regression.")
    terms=[]
    for c in predictors: terms.append(f'C(Q("{c}"))' if d[c].dtype=="object" else f'Q("{c}")')
    formula=f'Q("{outcome}") ~ '+' + '.join(terms or ['1'])
    return smf.quantreg(formula,d).fit(q=quantile)

def duration_sensitivity(df, outcome, duration_col, thresholds, animal_col=None):
    d=df.copy()
    d[outcome]=pd.to_numeric(d[outcome],errors="coerce")
    d[duration_col]=pd.to_numeric(d[duration_col],errors="coerce")
    rows=[]
    for t in thresholds:
        x=d[d[duration_col]>=t]
        y=x[outcome].dropna()
        rows.append({"minimum_duration_seconds":t,"n_records":len(y),"n_animals":x[animal_col].nunique() if animal_col and animal_col in x else np.nan,
                     "mean":float(y.mean()) if len(y) else np.nan,"sd":float(y.std()) if len(y)>1 else np.nan,
                     "median":float(y.median()) if len(y) else np.nan})
    return pd.DataFrame(rows)

def tost_independent(df,outcome,group,group_a,group_b,margin):
    d=df[[outcome,group]].copy();d[outcome]=pd.to_numeric(d[outcome],errors="coerce");d=d.dropna()
    a=d.loc[d[group]==group_a,outcome].to_numpy(float);b=d.loc[d[group]==group_b,outcome].to_numpy(float)
    if len(a)<3 or len(b)<3: raise ValueError("Each group needs at least three observations.")
    if margin<=0: raise ValueError("Equivalence margin must be positive and defined a priori.")
    # Welch standard error and df for difference B-A.
    diff=b.mean()-a.mean(); va=a.var(ddof=1)/len(a);vb=b.var(ddof=1)/len(b);se=np.sqrt(va+vb)
    dfree=(va+vb)**2/(va**2/(len(a)-1)+vb**2/(len(b)-1))
    t_lower=(diff+margin)/se; p_lower=stats.t.sf(t_lower,dfree)
    t_upper=(diff-margin)/se; p_upper=stats.t.cdf(t_upper,dfree)
    crit=stats.t.ppf(.95,dfree)
    return {"group_a":str(group_a),"group_b":str(group_b),"difference_b_minus_a":float(diff),
            "equivalence_margin":float(margin),"ci90_lower":float(diff-crit*se),"ci90_upper":float(diff+crit*se),
            "p_lower":float(p_lower),"p_upper":float(p_upper),"p_tost":float(max(p_lower,p_upper)),
            "equivalent_at_0.05":bool(p_lower<.05 and p_upper<.05),"n_a":len(a),"n_b":len(b),
            "interpretation":"Equivalence is supported only if both one-sided tests reject; margin must be scientifically justified before examining results."}

def cluster_stability(df, animal_col, features, k=3, n_boot=100, seed=42):
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import RobustScaler
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score
    rng=np.random.default_rng(seed)
    x=df.groupby(animal_col)[features].median().apply(pd.to_numeric,errors="coerce").dropna(how="all")
    if len(x)<max(10,k+2): raise ValueError("Insufficient animal profiles for stability analysis.")
    arr=RobustScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(x))
    base=KMeans(n_clusters=k,n_init=30,random_state=seed).fit_predict(arr)
    scores=[]
    for b in range(n_boot):
        idx=rng.choice(len(arr),size=len(arr),replace=True)
        if len(np.unique(idx))<k+1: continue
        # Fit on bootstrap sample and compare labels on sampled rows only.
        lab=KMeans(n_clusters=k,n_init=10,random_state=seed+b).fit_predict(arr[idx])
        scores.append(adjusted_rand_score(base[idx],lab))
    return {"n_animals":len(x),"k":k,"mean_ari":float(np.mean(scores)) if scores else np.nan,
            "median_ari":float(np.median(scores)) if scores else np.nan,"ari_sd":float(np.std(scores,ddof=1)) if len(scores)>1 else np.nan,
            "valid_bootstraps":len(scores),"note":"Bootstrap ARI is exploratory and can be optimistic because duplicated animals are reweighted; use independent resampling/stability design for publication."}
