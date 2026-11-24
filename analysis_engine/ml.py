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


def nested_grouped_regression_benchmark(df, outcome, features, animal_id,
                                       outer_splits=5, inner_splits=3,
                                       selected_models=None, random_state=42):
    """Nested animal-grouped CV for less optimistic model comparison.

    Hyperparameters are selected only inside each outer training fold. All records
    from an animal remain in the same outer and inner fold.
    """
    from sklearn.model_selection import GridSearchCV
    from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor, HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge, ElasticNet
    from sklearn.svm import SVR
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.base import clone

    if not features:
        raise ValueError("Select at least one predictor.")
    needed = list(dict.fromkeys([outcome, animal_id] + list(features)))
    d = df[needed].copy()
    d[outcome] = pd.to_numeric(d[outcome], errors="coerce")
    d = d.dropna(subset=[outcome, animal_id])
    d = d.loc[d[animal_id].notna()].copy()
    groups = d[animal_id].astype(str)
    n_groups = groups.nunique()
    if n_groups < 5:
        raise ValueError("Nested grouped validation requires at least five unique animals.")
    outer_n = min(int(outer_splits), n_groups)
    numeric = [c for c in features if pd.api.types.is_numeric_dtype(d[c])]
    categorical = [c for c in features if c not in numeric]
    prep = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                          ("scale", StandardScaler())]), numeric),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical)
    ])
    catalogue = {
        "Ridge": (Ridge(), {"model__alpha":[0.1, 1.0, 10.0, 100.0]}),
        "Elastic Net": (ElasticNet(max_iter=10000, random_state=random_state),
                        {"model__alpha":[0.001,0.01,0.1,1.0], "model__l1_ratio":[0.2,0.5,0.8]}),
        "Random Forest": (RandomForestRegressor(n_estimators=250, random_state=random_state, n_jobs=-1),
                          {"model__max_features":[0.7,1.0], "model__min_samples_leaf":[1,3,5]}),
        "Extra Trees": (ExtraTreesRegressor(n_estimators=250, random_state=random_state, n_jobs=-1),
                        {"model__max_features":[0.7,1.0], "model__min_samples_leaf":[1,3,5]}),
        "HistGradientBoosting": (HistGradientBoostingRegressor(random_state=random_state),
                                 {"model__learning_rate":[0.03,0.1], "model__max_iter":[100,200]}),
        "SVR": (SVR(), {"model__C":[0.1,1,10], "model__epsilon":[0.05,0.1,0.2]}),
        "KNN": (KNeighborsRegressor(), {"model__n_neighbors":[3,5,9], "model__weights":["uniform","distance"]}),
    }
    names = list(catalogue) if selected_models is None else list(selected_models)
    unknown = sorted(set(names)-set(catalogue))
    if unknown: raise ValueError(f"Unknown models: {unknown}")
    if not names: raise ValueError("Select at least one model.")
    outer = GroupKFold(n_splits=outer_n)
    rows=[]
    for name in names:
        estimator, grid = catalogue[name]
        oof=np.full(len(d), np.nan)
        fold_rows=[]
        errors=[]
        for fold,(tr,te) in enumerate(outer.split(d[features], d[outcome], groups), start=1):
            train_groups=groups.iloc[tr]
            inner_n=min(int(inner_splits), train_groups.nunique())
            if inner_n < 2:
                errors.append(f"Outer fold {fold}: fewer than two training groups for inner CV.")
                continue
            pipe=Pipeline([("prep",clone(prep)),("model",clone(estimator))])
            search=GridSearchCV(pipe, grid, cv=GroupKFold(n_splits=inner_n),
                                scoring="neg_root_mean_squared_error", n_jobs=-1,
                                refit=True, error_score="raise")
            try:
                search.fit(d.iloc[tr][features], d.iloc[tr][outcome],
                           groups=train_groups)
                pred=search.predict(d.iloc[te][features])
                oof[te]=pred
                fold_rows.append({"fold":fold,"n_test_animals":int(groups.iloc[te].nunique()),
                                  "n_test_records":int(len(te)),
                                  "rmse":float(np.sqrt(mean_squared_error(d.iloc[te][outcome],pred))),
                                  "mae":float(mean_absolute_error(d.iloc[te][outcome],pred)),
                                  "best_params":search.best_params_})
            except Exception as exc:
                errors.append(f"Outer fold {fold}: {type(exc).__name__}: {str(exc)[:180]}")
        valid=np.isfinite(oof)
        if valid.sum() == 0:
            rows.append({"model":name,"error":"; ".join(errors) or "No valid outer-fold predictions"})
            continue
        y=d[outcome].to_numpy()[valid]; pred=oof[valid]
        rows.append({"model":name,"n_animals":int(groups.nunique()),
                     "n_records":int(valid.sum()),"outer_folds_completed":len(fold_rows),
                     "rmse":float(np.sqrt(mean_squared_error(y,pred))),
                     "mae":float(mean_absolute_error(y,pred)),
                     "r2":float(r2_score(y,pred)) if len(y)>1 else np.nan,
                     "mean_prediction_bias":float(np.mean(pred-y)),
                     "fold_details":fold_rows,"warnings":errors})
    result = pd.DataFrame(rows)
    return result.sort_values("rmse",na_position="last") if "rmse" in result.columns else result
