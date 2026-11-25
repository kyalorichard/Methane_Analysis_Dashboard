import numpy as np
import pandas as pd
from analysis_engine.settings_runtime import preprocess_frame, settings_consumption_report
from analysis_engine.service_registry import get_service, service_names


def test_preprocessing_outlier_flag_preserves_rows_and_flags():
    df=pd.DataFrame({'x':[1.,2.,3.,4.,100.], 'group':['a']*5})
    out,audit=preprocess_frame(df, {'preprocessing':{'outlier_method':'IQR','outlier_action':'flag','outlier_threshold':1.5,'missing_threshold_pct':100,'duplicate_action':'flag','transformation':'none'}})
    assert len(out)==len(df)
    assert out['x__outlier_flag'].sum()==1
    assert audit['output_rows']==5


def test_preprocessing_cap_changes_extreme_value():
    df=pd.DataFrame({'x':[1.,2.,3.,4.,100.]})
    out,_=preprocess_frame(df, {'preprocessing':{'outlier_method':'IQR','outlier_action':'cap','outlier_threshold':1.5,'missing_threshold_pct':100,'duplicate_action':'flag','transformation':'none'}})
    assert out['x'].max()<100


def test_high_missingness_columns_removed_only_when_configured():
    df=pd.DataFrame({'x':[1,None,None,None], 'y':[1,2,3,4]})
    out,audit=preprocess_frame(df, {'preprocessing':{'missing_threshold_pct':50,'duplicate_action':'flag','outlier_action':'flag','outlier_method':'IQR','transformation':'none'}})
    assert 'x' not in out and audit['dropped_columns']==['x']


def test_registry_resolves_shared_services():
    assert 'fit_ols' in service_names()
    assert callable(get_service('fit_ols'))
    assert callable(get_service('compare_forecasters'))


def test_settings_contract_contains_all_default_paths():
    from analysis_engine.settings_config import defaults
    report=settings_consumption_report(defaults())
    assert len(report)>50
    assert report['configured'].all()
