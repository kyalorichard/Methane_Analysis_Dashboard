
import pandas as pd
from analysis_engine.emitters import build_emitter_cohorts, emitter_group_summary

def test_animal_level_percentile_cohorts_use_median():
    df = pd.DataFrame({
        "AnimalID": ["A","A","B","B","C","C","D","D","E","E"],
        "mean_methane": [1,3,2,4,5,7,8,10,11,13],
        "weight": [20,22,21,23,24,26,27,29,30,32],
        "Breed": ["X"]*4+["Y"]*6
    })
    cohorts, meta = build_emitter_cohorts(df, "mean_methane", 20, "AnimalID", "median", 1)
    assert len(cohorts) == 5
    assert cohorts["AnimalID"].is_unique
    assert meta["n_low"] == 1
    assert meta["n_high"] == 1
    assert cohorts.loc[cohorts.AnimalID == "A", "mean_methane"].iloc[0] == 2

def test_record_level_fallback_when_no_animal_id():
    df = pd.DataFrame({"mean_methane":[1,2,3,4,5]})
    cohorts, meta = build_emitter_cohorts(df, "mean_methane", 20, None)
    assert len(cohorts) == 5
    assert meta["animal_level"] is False

def test_invalid_tail_percent_rejected():
    import pytest
    with pytest.raises(ValueError):
        build_emitter_cohorts(pd.DataFrame({"x":[1,2]}), "x", 30)
