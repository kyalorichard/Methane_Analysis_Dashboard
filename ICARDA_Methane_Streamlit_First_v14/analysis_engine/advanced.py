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
    """One-way random-effects ICC(1,1) and ICC(1,k), with balanced-design caveat."""
    d=df[[animal_col,value_col]+([session_col] if session_col else [])].copy()
    d[value_col]=pd.to_numeric(d[value_col],errors="coerce")
    d=d.dropna(subset=[animal_col,value_col])
    counts=d.groupby(animal_col)[value_col].size()
    eligible=counts[counts>=min_repeats].index
    d=d[d[animal_col].isin(eligible)]
    if d[animal_col].nunique()<3: raise ValueError("At least three animals with repeated observations are required.")
    groups=[g[value_col].to_numpy(float) for _,g in d.groupby(animal_col)]
    n=len(groups); k=int(round(np.mean([len(g) for g in groups])))
    grand=d[value_col].mean()
    ssb=sum(len(g)*(g.mean()-grand)**2 for g in groups)
    ssw=sum(((g-g.mean())**2).sum() for g in groups)
    msb=ssb/(n-1); msw=ssw/(len(d)-n)
    # Unequal replicate counts: use harmonic mean in the ICC(1,1) denominator.
    nh=n/(sum(1/len(g) for g in groups))
    icc1=(msb-msw)/(msb+(nh-1)*msw) if (msb+(nh-1)*msw)!=0 else np.nan
    icck=(msb-msw)/msb if msb!=0 else np.nan
    return {"n_animals":n,"n_records":len(d),"mean_repeats":float(np.mean([len(g) for g in groups])),
            "min_repeats":int(min(len(g) for g in groups)),"max_repeats":int(max(len(g) for g in groups)),
            "MS_between":float(msb),"MS_within":float(msw),"ICC_single":float(icc1),
            "ICC_average":float(icck),"design_note":"Unequal replicate counts; harmonic-mean approximation. Use a two-way mixed-effects ICC when sessions are fixed and fully crossed."}

def bootstrap_icc(df, animal_col, value_col, n_boot=500, seed=42):
    rng=np.random.default_rng(seed)
    ids=df[animal_col].dropna().unique()
    if len(ids)<4: raise ValueError("At least four animals are required for animal-level bootstrap.")
    vals=[]
    for _ in range(n_boot):
        sampled=rng.choice(ids,size=len(ids),replace=True)
        parts=[]
        for j,a in enumerate(sampled):
            g=df.loc[df[animal_col]==a].copy()
            g[animal_col]=f"boot_{j}"
            parts.append(g)
        b=pd.concat(parts,ignore_index=True)
        try: vals.append(repeatability_icc(b,animal_col,value_col)["ICC_single"])
        except Exception: pass
    if len(vals)<max(30,n_boot*.5): raise ValueError("Too few valid bootstrap replicates.")
    return {"estimate":float(np.nanmedian(vals)),"ci_low":float(np.nanquantile(vals,.025)),
            "ci_high":float(np.nanquantile(vals,.975)),"valid_bootstraps":len(vals),"n_boot":n_boot}

def bland_altman(df, animal_col, value_col, session_col, session_a, session_b):
    d=df[[animal_col,session_col,value_col]].copy()
    d[value_col]=pd.to_numeric(d[value_col],errors="coerce")
    d=d.dropna().groupby([animal_col,session_col])[value_col].mean().unstack(session_col)
    if session_a not in d or session_b not in d: raise ValueError("Both selected sessions must be present.")
    x=d[[session_a,session_b]].dropna()
    if len(x)<3: raise ValueError("At least three paired animals are required.")
    mean=(x[session_a]+x[session_b])/2
    diff=x[session_b]-x[session_a]
    bias=diff.mean(); sd=diff.std(ddof=1)
    return pd.DataFrame({"animal_mean":mean,"difference_b_minus_a":diff}), {
        "n_pairs":len(x),"bias":float(bias),"sd_difference":float(sd),
        "loa_lower":float(bias-1.96*sd),"loa_upper":float(bias+1.96*sd)}

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

def fit_quantile_regression(df,outcome,predictors,quantile=.5):
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
