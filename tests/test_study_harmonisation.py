import numpy as np
import pandas as pd
import pytest
from analysis_engine.study_harmonisation import harmonise_study_frame, audit_protocol_comparability, dersimonian_laird

def test_explicit_harmonisation_mapping_and_conversion():
    x=pd.DataFrame({'animal':['a','b'],'ch4':[10,20],'mass':[100,120]})
    out=harmonise_study_frame(x,study_id='S1',species='sheep',column_mapping={'animal_id':'animal','methane_value':'ch4','body_weight_kg':'mass'},unit='g/day',phenotype='production',phenotype_definition='daily mass flux',measurement_method='chamber',instrument='I1',calibration_reference='CAL1',conversion_factor=.001)
    assert out.methane_value.tolist()==[.01,.02]
    assert set(['study_id','species','unit','measurement_method']).issubset(out.columns)

def test_harmonisation_requires_existing_source_columns():
    with pytest.raises(ValueError):
        harmonise_study_frame(pd.DataFrame({'x':[1]}),study_id='S',species='goat',column_mapping={'methane_value':'missing'},unit='g/day',phenotype='production',phenotype_definition='x',measurement_method='m',instrument='i',calibration_reference='c')

def test_protocol_audit_flags_different_units_and_definitions():
    d=pd.DataFrame([{'species':'sheep','phenotype':'production','phenotype_definition':'mass/time','unit':'g/day','measurement_method':'chamber','instrument':'A','calibration_reference':'C'}, {'species':'sheep','phenotype':'production','phenotype_definition':'mass/time','unit':'ppm','measurement_method':'chamber','instrument':'A','calibration_reference':'C'}])
    result=audit_protocol_comparability(d)
    assert not result['comparable'] and 'unit' in result['differences']

def test_random_effects_meta_analysis():
    r=dersimonian_laird([.2,.4,.3],[.1,.15,.12])
    assert r['n_studies']==3 and r['ci_low']<r['pooled_effect']<r['ci_high']
    assert r['tau_squared']>=0 and 0<=r['i_squared_percent']<=100

def test_meta_analysis_rejects_single_study():
    with pytest.raises(ValueError): dersimonian_laird([.2],[.1])
