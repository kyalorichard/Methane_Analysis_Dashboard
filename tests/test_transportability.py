import numpy as np
import pandas as pd
import pytest
from analysis_engine.transportability import (audit_external_cohort, distribution_shift_report,
    cluster_bootstrap_regression, paired_model_comparison)


def cohorts():
    rng=np.random.default_rng(9)
    dev=pd.DataFrame({'animal':[f'A{i}' for i in range(30)],'farm':[f'F{i//3}' for i in range(30)],'x':rng.normal(0,1,30),'breed':rng.choice(['A','B'],30)})
    ext=pd.DataFrame({'animal':[f'B{i}' for i in range(20)],'farm':[f'G{i//2}' for i in range(20)],'x':rng.normal(1,1.2,20),'breed':rng.choice(['A','C'],20)})
    return dev,ext


def test_external_audit_flags_identifier_overlap_and_missing_schema():
    d,e=cohorts(); e.loc[0,'animal']=d.loc[0,'animal']
    r=audit_external_cohort(d,e,animal_id='animal',group_id='farm',required_columns=['x','breed','outcome'])
    assert not r['independence_screen_passed']
    assert r['identifier_audit']['animal']['overlap_count']==1
    assert r['missing_from_external']==['outcome']


def test_external_audit_no_overlap_is_only_screen_not_proof():
    d,e=cohorts(); r=audit_external_cohort(d,e,animal_id='animal',group_id='farm')
    assert r['independence_screen_passed']
    assert 'not proof' in r['interpretation']


def test_distribution_shift_numeric_and_categorical():
    d,e=cohorts(); out=distribution_shift_report(d,e,['x','breed'])
    assert out.loc[out.feature=='x','standardized_mean_difference'].notna().all()
    assert out.loc[out.feature=='breed','max_category_prevalence_difference'].notna().all()


def test_cluster_bootstrap_and_paired_comparison_reproducible():
    rng=np.random.default_rng(2); groups=np.repeat([f'F{i}' for i in range(12)],5)
    y=rng.normal(size=len(groups)); p1=y+rng.normal(0,.8,len(y)); p2=y+rng.normal(0,.4,len(y))
    a=cluster_bootstrap_regression(y,p2,groups,n_boot=250,random_state=12)
    b=cluster_bootstrap_regression(y,p2,groups,n_boot=250,random_state=12)
    assert a==b and a['n_clusters']==12
    cmp=paired_model_comparison(y,{'Conventional':p1,'ML':p2},groups,n_boot=250,random_state=12)
    assert set(cmp.metric)=={'mae','rmse'} and cmp.iloc[0].candidate_model=='ML'


def test_cluster_bootstrap_requires_independent_clusters():
    with pytest.raises(ValueError,match='five independent clusters'):
        cluster_bootstrap_regression([1,2,3,4],[1,2,3,4],['a','a','b','b'],n_boot=200)
