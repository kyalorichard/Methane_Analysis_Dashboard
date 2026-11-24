import numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor,ExtraTreesRegressor,HistGradientBoostingRegressor,RandomForestClassifier,ExtraTreesClassifier
from sklearn.linear_model import Ridge,ElasticNet,LogisticRegression
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.model_selection import GroupKFold,cross_validate
from sklearn.metrics import make_scorer,mean_absolute_error,root_mean_squared_error,r2_score
from sklearn.base import clone

REGRESSORS={"Ridge":Ridge(),"Elastic Net":ElasticNet(max_iter=10000),"Random Forest":RandomForestRegressor(n_estimators=300,random_state=42,n_jobs=-1),"Extra Trees":ExtraTreesRegressor(n_estimators=300,random_state=42,n_jobs=-1),"HistGradientBoosting":HistGradientBoostingRegressor(random_state=42),"SVR":SVR(),"KNN":KNeighborsRegressor()}
def grouped_regression_benchmark(df,outcome,features,animal_id,n_splits=5,selected_models=None):
    d=df[[outcome,animal_id]+features].dropna(subset=[outcome,animal_id]).copy()
    y=pd.to_numeric(d[outcome],errors="coerce")
    valid=y.notna(); d=d.loc[valid]; y=y.loc[valid]
    if d[animal_id].nunique()<3: raise ValueError("At least three unique animals are required for grouped validation.")
    groups=d[animal_id].astype(str)
    n_splits=min(n_splits,groups.nunique())
    numeric=[c for c in features if pd.api.types.is_numeric_dtype(d[c])]
    categorical=[c for c in features if c not in numeric]
    prep=ColumnTransformer([
      ("num",Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler())]),numeric),
      ("cat",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore",sparse_output=False))]),categorical)
    ])
    cv=GroupKFold(n_splits=n_splits)
    rows=[]
    model_names = list(REGRESSORS) if selected_models is None else list(selected_models)
    unknown = sorted(set(model_names) - set(REGRESSORS))
    if unknown: raise ValueError(f"Unknown model names: {unknown}")
    if not model_names: raise ValueError("Select at least one model to benchmark.")
    for name in model_names:
        model = REGRESSORS[name]
        pipe=Pipeline([("prep",prep),("model",clone(model))])
        try:
            scores=cross_validate(pipe,d[features],y,groups=groups,cv=cv,
                scoring={"r2":"r2","mae":"neg_mean_absolute_error","rmse":"neg_root_mean_squared_error"},
                error_score="raise")
            rows.append({"model":name,"n_animals":groups.nunique(),"n_records":len(d),
              "r2_mean":scores["test_r2"].mean(),"r2_sd":scores["test_r2"].std(),
              "mae_mean":-scores["test_mae"].mean(),"rmse_mean":-scores["test_rmse"].mean()})
        except Exception as e: rows.append({"model":name,"error":str(e)[:240]})
    return pd.DataFrame(rows).sort_values("rmse_mean",na_position="last")
