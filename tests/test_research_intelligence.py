import numpy as np
import pandas as pd
from analysis_engine.research_intelligence import (
    dataframe_fingerprint, dataset_readiness, automated_recommendations,
    flag_data_quality, calibration_diagnostics, phenotype_evidence_matrix,
    compare_run_manifests
)

def sample():
    return pd.DataFrame({
        "AnimalID":["A","A","B","B","C","C"],
        "CH4":[1.0,1.2,2.0,2.1,3.0,3.2],
        "duration":[60,70,60,70,60,70],
        "weight":[20,21,25,25,30,31],
    })

def test_fingerprint_changes_with_data():
    d=sample()
    assert dataframe_fingerprint(d)==dataframe_fingerprint(d.copy())
    d.loc[0,"CH4"]=99
    assert dataframe_fingerprint(d)!=dataframe_fingerprint(sample())

def test_readiness_and_recommendations():
    d=sample()
    roles={"animal_id":"AnimalID","methane":"CH4","recording_duration":"duration"}
    r=dataset_readiness(d,roles,{"units":"ppm","instrument":"LMD","calibration_status":"Not documented"})
    assert r["n_animals"]==3 and r["readiness_pct"]>0
    assert any("grouped" in x["analysis"].lower() for x in automated_recommendations(d,roles))

def test_qc_flags_without_modifying_source():
    d=sample()
    d.loc[0,"CH4"]=-10
    original=d.copy(deep=True)
    flags=flag_data_quality(d,["CH4"],nonnegative_columns=["CH4"])
    assert "Negative value" in " ".join(flags["flags"])
    pd.testing.assert_frame_equal(d,original)

def test_calibration_diagnostics_and_evidence():
    d=pd.DataFrame({"reference":[1,2,3,4,5],"measured":[1.1,1.9,3.2,3.8,5.1]})
    metrics,pairs=calibration_diagnostics(d,"reference","measured")
    assert metrics["n_pairs"]==5 and "difference_measured_minus_reference" in pairs
    ev=phenotype_evidence_matrix(d,["measured"])
    assert ev.loc[0,"n_valid_records"]==5

def test_manifest_comparison():
    diff=compare_run_manifests({"a":1,"b":{"x":2}},{"a":1,"b":{"x":3}})
    assert diff["changed"].sum()==1
