import streamlit as st, pandas as pd, plotly.express as px
from sklearn.inspection import permutation_importance
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_squared_error,mean_absolute_error,r2_score
from sklearn.base import clone
from analysis_engine.ml import REGRESSORS
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
from analysis_engine.settings_config import load_active_settings
render_sidebar_navigation()
_cfg = load_active_settings(st.session_state)
_cmp_cfg = _cfg.get("comparison", {})

header('Variable importance & model explainability','Compare selected regression models and estimate predictor importance using a held-out set of animals.')
df=get_data();nums=numeric_cols(df);r=get_roles(df);ycol=choose_col(df,'Target',r.get('methane'),nums);animal=choose_col(df,'Animal ID',r.get('animal_id'))
features=st.multiselect('Predictors',[c for c in df.columns if c not in [ycol,animal]],default=[c for c in nums if c!=ycol][:6])
model_names=list(REGRESSORS)
mode=st.radio('Models to explain',['Compare all available models','Select specific models'],horizontal=True,key='importance_selection_mode')
selected=model_names if mode.startswith('Compare') else st.multiselect('Models for importance assessment',model_names,default=model_names[:3],key='importance_selected_models')
repeats=st.slider('Permutation repeats',5,30,10)
test_fraction=float(_cmp_cfg.get('test_size', 0.25))
random_seed=int(_cmp_cfg.get('random_state', 42))
group_column=str(_cmp_cfg.get('group_column') or animal)
if group_column not in df.columns: group_column = animal
if group_column != animal: st.info(f'Central validation grouping is configured as {group_column}; this page uses the selected Animal ID column ({animal}) for its animal-held-out explanation split.')
if st.button('Fit selected models and calculate variable importance',type='primary',disabled=(not features or not selected)):
    d=df[[ycol,animal]+features].copy();d[ycol]=pd.to_numeric(d[ycol],errors='coerce');d=d.dropna(subset=[ycol,animal])
    if d[animal].nunique()<5: st.error('At least five unique animals are required for a grouped holdout split.')
    else:
        split=GroupShuffleSplit(n_splits=1,test_size=test_fraction,random_state=random_seed);tr,te=next(split.split(d[features],d[ycol],groups=d[animal]))
        Xtr,Xte=d.iloc[tr][features],d.iloc[te][features];ytr,yte=d.iloc[tr][ycol],d.iloc[te][ycol]
        num=[c for c in features if pd.api.types.is_numeric_dtype(d[c])];cat=[c for c in features if c not in num]
        prep=ColumnTransformer([('num',Pipeline([('imp',SimpleImputer(strategy='median')),('scale',StandardScaler())]),num),('cat',Pipeline([('imp',SimpleImputer(strategy='most_frequent')),('oh',OneHotEncoder(handle_unknown='ignore'))]),cat)])
        metric_rows=[];importance_rows=[]
        progress=st.progress(0)
        for i,name in enumerate(selected):
            try:
                model=Pipeline([('prep',clone(prep)),('model',clone(REGRESSORS[name]))]);model.fit(Xtr,ytr);pred=model.predict(Xte)
                metric_rows.append({'model':name,'heldout_animals':d.iloc[te][animal].nunique(),'n_test_records':len(te),'rmse':mean_squared_error(yte,pred)**.5,'mae':mean_absolute_error(yte,pred),'r2':r2_score(yte,pred)})
                pi=permutation_importance(model,Xte,yte,n_repeats=repeats,random_state=random_seed,scoring='neg_root_mean_squared_error')
                for f,mean,sd in zip(features,pi.importances_mean,pi.importances_std): importance_rows.append({'model':name,'feature':f,'importance_mean':mean,'importance_sd':sd})
            except Exception as e: metric_rows.append({'model':name,'error':str(e)[:200]})
            progress.progress((i+1)/len(selected))
        st.session_state['importance_metrics']=pd.DataFrame(metric_rows)
        st.session_state['importance_results']=pd.DataFrame(importance_rows)
        st.session_state['importance_holdout_animals']=d.iloc[te][animal].nunique()
metrics=st.session_state.get('importance_metrics');imp=st.session_state.get('importance_results')
if metrics is not None:
    st.subheader('Held-out model performance')
    st.caption(f"Animal-grouped holdout: {st.session_state.get('importance_holdout_animals')} test animals; all records for each animal remain together.")
    st.dataframe(metrics,use_container_width=True)
    st.download_button('Download model performance',metrics.to_csv(index=False).encode(),'explainability_model_metrics.csv','text/csv')
if imp is not None and not imp.empty:
    st.subheader('Permutation-based variable importance')
    st.caption('Importance is the increase in held-out RMSE when a feature is permuted; larger positive values indicate greater predictive reliance. Negative values can occur.')
    for name in imp['model'].unique():
        part=imp[imp.model==name].sort_values('importance_mean',ascending=True)
        st.plotly_chart(px.bar(part,x='importance_mean',y='feature',orientation='h',error_x='importance_sd',title=f'{name}: held-out permutation importance'),use_container_width=True)
    st.dataframe(imp,use_container_width=True)
    st.download_button('Download variable importance table',imp.to_csv(index=False).encode(),'variable_importance_by_model.csv','text/csv')
st.info('Permutation importance is model- and holdout-dependent, not a causal effect. Correlated predictors can share or mask importance. Interpret importance alongside biological plausibility, uncertainty, measurement quality, and external validation. Importance from one grouped holdout is exploratory; repeated grouped resampling is recommended for publication-grade stability estimates.')

st.page_link("pages/34_Advanced_ML_Explainability.py", label="Open advanced explainability and validation", icon="💡")
