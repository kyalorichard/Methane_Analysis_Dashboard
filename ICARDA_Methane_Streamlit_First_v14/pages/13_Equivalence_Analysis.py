import streamlit as st, pandas as pd, numpy as np
from scipy import stats
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Equivalence analysis','Test whether a two-group contrast falls within a prespecified practical equivalence margin.')
df=get_data();nums=numeric_cols(df);groups=[c for c in df.columns if 2<=df[c].nunique(dropna=True)<=10]
g=choose_col(df,'Grouping variable',get_roles(df).get('breed'),groups);out=choose_col(df,'Outcome',get_roles(df).get('methane'),nums)
levels=list(df[g].dropna().unique())
if len(levels)!=2: st.error('Select a grouping variable with exactly two observed groups.');st.stop()
a,b=st.columns(2);g1=a.selectbox('Group A',levels,index=0);g2=b.selectbox('Group B',levels,index=1)
margin=st.number_input('Equivalence margin (± outcome units)',min_value=0.0001,value=1.0,step=.1,format='%.4f')
d=df[[g,out]].copy();d[out]=pd.to_numeric(d[out],errors='coerce');x=d.loc[d[g]==g1,out].dropna().values;y=d.loc[d[g]==g2,out].dropna().values
if len(x)>=2 and len(y)>=2:
    diff=x.mean()-y.mean();se=np.sqrt(x.var(ddof=1)/len(x)+y.var(ddof=1)/len(y));dfree=(x.var(ddof=1)/len(x)+y.var(ddof=1)/len(y))**2/((x.var(ddof=1)/len(x))**2/(len(x)-1)+(y.var(ddof=1)/len(y))**2/(len(y)-1));crit=stats.t.ppf(.95,dfree);lo,hi=diff-crit*se,diff+crit*se
    metric_row([('MEAN DIFFERENCE',f'{diff:.3f}','Group A minus Group B'),('90% CI',f'[{lo:.3f}, {hi:.3f}]','Welch interval'),('EQUIVALENCE MARGIN',f'±{margin:.3f}','User specified')])
    if lo>-margin and hi<margin: st.success('The 90% confidence interval lies within the prespecified equivalence bounds (Welch two-sample TOST logic).')
    else: st.warning('Equivalence was not demonstrated: the 90% confidence interval extends beyond at least one equivalence bound.')
    st.caption(f'nA={len(x)}; nB={len(y)}. This is an unadjusted independent-sample calculation; repeated animal data require a model-based contrast and corresponding TOST.')
else: st.info('At least two observations per group are required.')
st.warning('The equivalence margin must be justified scientifically and set before examining results. A non-significant difference does not establish equivalence.')
