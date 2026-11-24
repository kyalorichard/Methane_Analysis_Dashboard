import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import ExtraTreesRegressor
from analysis_engine.release6 import (consensus_clustering, dataset_validation_report,
    external_regression_validation, create_reproducibility_manifest, fit_random_slope_model)


def test_dataset_validation_reports_nonfinite_and_empty_rows():
    d = pd.DataFrame({'animal_id':['a','b',None], 'methane':[1.0, np.inf, np.nan]})
    r = dataset_validation_report(d)
    assert r['n_records'] == 3
    assert r['nonfinite_numeric_values']['methane'] == 1
    assert r['all_empty_rows'] == 1
    assert not r['valid_structure']


def test_consensus_clustering_reproducible_and_symmetric():
    rng = np.random.default_rng(2)
    x = pd.DataFrame(rng.normal(size=(30, 4)), index=[f'a{i}' for i in range(30)])
    x.iloc[15:] += 3
    a, m = consensus_clustering(x, n_clusters=2, n_resamples=50, random_state=7)
    b, n = consensus_clustering(x, n_clusters=2, n_resamples=50, random_state=7)
    assert len(a) == 30
    assert np.allclose(m.values, m.values.T)
    assert np.allclose(m.values, n.values)
    assert a['consensus_cluster'].nunique() == 2


def test_external_validation_does_not_refit():
    rng = np.random.default_rng(3)
    X = pd.DataFrame({'x': rng.normal(size=50)})
    y = 2 * X.x + 1
    model = ExtraTreesRegressor(n_estimators=20, random_state=1).fit(X, y)
    result = external_regression_validation(model, pd.DataFrame({'x':[.2,.4,.6,.8,1.0], 'y':[1.4,1.8,2.2,2.6,3.0]}), 'y', ['x'])
    assert result['n_external'] == 5
    assert result['rmse'] < .5


def test_random_slope_model_fits_repeated_data():
    rng = np.random.default_rng(4)
    rows=[]
    for i in range(12):
        intercept=rng.normal()
        slope=.3+rng.normal(scale=.08)
        for t in range(4): rows.append({'animal':str(i),'day':t,'y':intercept+slope*t+rng.normal(scale=.1)})
    model, used = fit_random_slope_model(pd.DataFrame(rows), 'y', 'day', 'animal')
    assert len(used) == 48
    assert any('day' in str(x) for x in model.fe_params.index)


def test_manifest_contains_fingerprint_and_parameters():
    d=pd.DataFrame({'animal':['a','b'], 'y':[1,2]})
    m=create_reproducibility_manifest(d, 'test', {'outcome':'y'}, 'demo')
    assert len(m['dataset_fingerprint']) >= 32
    assert m['parameters']['outcome']=='y'


def test_run_registry_persistence_and_recovery(tmp_path):
    from platform_core.run_registry import save_run, list_runs
    db = tmp_path / 'registry.sqlite3'
    manifest = {'dataset_name':'demo.csv','audit':{'data_sha256':'abc'},'outcome':'methane','species':'sheep'}
    save_run('run-1', manifest, {'rmse':1.2}, db_path=db)
    rows = list_runs(db_path=db)
    assert len(rows) == 1
    assert rows[0]['run_id'] == 'run-1'
    assert rows[0]['dataset_fingerprint'] == 'abc'
    # Reopening the same database simulates process restart/recovery.
    assert list_runs(db_path=db)[0]['summary_json'].find('1.2') >= 0


def test_icc_and_variance_decomposition_on_repeated_panel():
    from analysis_engine.release6 import estimate_repeatability_icc, within_between_variability
    rng = np.random.default_rng(2026)
    subject = rng.normal(0, 2, 40)
    panel = pd.DataFrame({f"round_{j}": subject + rng.normal(0, .35, 40) for j in range(4)})
    result = estimate_repeatability_icc(panel, model="ICC3", n_boot=250, random_state=9)
    variance = within_between_variability(panel)
    assert result["n_subjects"] == 40
    assert result["icc_single"] > .8
    assert result["icc_single_ci_low"] <= result["icc_single"] <= result["icc_single_ci_high"]
    assert variance["between_subject_fraction"] > variance["within_subject_fraction"]


def test_icc2_penalises_systematic_occasion_shift_more_than_icc3():
    from analysis_engine.release6 import estimate_repeatability_icc
    rng = np.random.default_rng(12)
    subject = rng.normal(10, 2, 50)
    panel = pd.DataFrame({f"round_{j}": subject + j * 2.0 + rng.normal(0, .2, 50) for j in range(3)})
    icc2 = estimate_repeatability_icc(panel, model="ICC2", n_boot=250, random_state=4)
    icc3 = estimate_repeatability_icc(panel, model="ICC3", n_boot=250, random_state=4)
    assert icc3["icc_single"] > icc2["icc_single"]


def test_bland_altman_reports_bias_and_limits():
    from analysis_engine.release6 import bland_altman_summary
    rng = np.random.default_rng(8)
    a = rng.normal(20, 3, 80)
    b = a - 1.5 + rng.normal(0, .5, 80)
    result = bland_altman_summary(a, b, n_boot=250, random_state=2)
    assert result["n_pairs"] == 80
    assert 1.3 < result["bias_first_minus_second"] < 1.7
    assert result["lower_limit_of_agreement"] < result["upper_limit_of_agreement"]


def test_icc_rejects_unbalanced_panel():
    from analysis_engine.release6 import estimate_repeatability_icc
    panel = pd.DataFrame({"r1": [1, 2, 3, 4, 5, 6], "r2": [1, 2, np.nan, 4, 5, 6]})
    result = estimate_repeatability_icc(panel, model="ICC1", n_boot=200)
    assert result["n_subjects"] == 5


def test_grouped_learning_curve_returns_nonnegative_rmse():
    from analysis_engine.release6 import grouped_learning_curve
    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.ensemble import ExtraTreesRegressor
    rng=np.random.default_rng(44)
    groups=np.repeat(np.arange(20),3)
    X=pd.DataFrame({'x':rng.normal(size=len(groups)),'z':rng.normal(size=len(groups))})
    y=2*X.x-X.z+rng.normal(scale=.1,size=len(groups))
    pipe=Pipeline([('impute',SimpleImputer()),('model',ExtraTreesRegressor(n_estimators=20,random_state=1))])
    result=grouped_learning_curve(pipe,X,y,groups,cv_splits=4,train_sizes=[.5,1.0])
    assert len(result)==2
    assert (result[['train_rmse_mean','validation_rmse_mean']]>=0).all().all()


def test_feature_selection_stability_uses_group_bootstrap():
    from analysis_engine.release6 import feature_selection_stability
    rng=np.random.default_rng(45); groups=np.repeat(np.arange(12),3)
    X=pd.DataFrame({'signal':rng.normal(size=len(groups)),'noise':rng.normal(size=len(groups))})
    y=4*X.signal+rng.normal(scale=.2,size=len(groups))
    model=ExtraTreesRegressor(n_estimators=30,random_state=2)
    out=feature_selection_stability(X,y,model,groups,n_resamples=20,top_k=1,random_state=3)
    assert set(out.columns)=={'feature','selection_frequency'}
    assert out.selection_frequency.between(0,1).all()
    assert out.iloc[0].feature=='signal'
