import numpy as np
import pandas as pd
from analysis_engine.advanced import repeatability_icc, group_comparison, tost_independent, duration_sensitivity

def sample_data():
    rng=np.random.default_rng(17)
    rows=[]
    for i in range(40):
        base=rng.normal(10,2)
        for r in [1,2,3]:
            rows.append({"AnimalID":f"A{i}","Round":f"R{r}","Breed":"A" if i<20 else "B",
                         "methane":base+rng.normal(0,0.7),"duration":180+rng.normal(0,10)})
    return pd.DataFrame(rows)

def test_icc_uses_repeated_animals():
    d=sample_data()
    result=repeatability_icc(d,"AnimalID","methane")
    assert result["n_animals"]==40
    assert result["ICC_single"]>0

def test_group_comparison_returns_effect_and_pvalue():
    d=sample_data()
    result=group_comparison(d.groupby(["AnimalID","Breed"],as_index=False)["methane"].mean(),"methane","Breed")
    assert 0 <= result["p_value"] <= 1
    assert "cohen_d_approx" in result

def test_tost_reports_margin_and_decision():
    d=sample_data()
    result=tost_independent(d.groupby(["AnimalID","Breed"],as_index=False)["methane"].mean(),"methane","Breed","A","B",5.0)
    assert result["equivalence_margin"]==5.0
    assert isinstance(result["equivalent_at_0.05"],bool)

def test_duration_sensitivity_uses_configured_animal_column():
    d=sample_data()
    result=duration_sensitivity(d,"methane","duration",[180], "AnimalID")
    assert result.loc[0,"n_animals"]>=20
