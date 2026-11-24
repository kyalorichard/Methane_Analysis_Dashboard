import numpy as np
import pandas as pd
from analysis_engine.phenotype_validation import distribution_diagnostics, group_profile, repeated_measure_diagnostics, correlate_with_covariate


def test_distribution_diagnostics():
    d = pd.DataFrame({'x':[1,2,3,4,np.nan,100]})
    r = distribution_diagnostics(d, 'x')
    assert r['n_valid'] == 5 and r['n_missing'] == 1
    assert r['iqr_outlier_n'] >= 1


def test_group_profile():
    d = pd.DataFrame({'x':[1,2,3,4], 'breed':['A','A','B','B']})
    r = group_profile(d, 'x', 'breed')
    assert list(r['n']) == [2,2]


def test_repeated_measure_diagnostics():
    d = pd.DataFrame({'AnimalID':np.repeat(np.arange(10),2), 'Round':['R1','R2']*10,
                      'x':np.repeat(np.arange(10),2)+np.tile([0,.2],10)})
    r, s, p = repeated_measure_diagnostics(d, 'AnimalID', 'x', 'Round')
    assert r['n_animals_repeated'] == 10
    assert 'ICC_single' in r
    assert len(p) == 10 and len(s) == 2


def test_covariate_correlation_animal_aggregate():
    d = pd.DataFrame({'AnimalID':np.repeat(np.arange(8),2), 'x':np.repeat(np.arange(8),2),
                      'w':np.repeat(np.arange(8)*2,2)})
    r, points = correlate_with_covariate(d, 'x', 'w', 'AnimalID')
    assert r['n_units'] == 8
    assert r['spearman_rho'] > .99
