
import numpy as np
import pandas as pd
import pytest
from analysis_engine.phenotype_builder import create_derived_phenotype, evaluate_phenotype_formula, FormulaError
from analysis_engine.emitter_tracking import classify_emitters_by_round, emitter_persistence_summary

def test_formula_creates_derived_variable():
    df=pd.DataFrame({"mean_methane":[10.,20.,30.],"weight":[2.,4.,5.]})
    out=create_derived_phenotype(df,"methane_per_kg","mean_methane / weight")
    assert np.allclose(out.methane_per_kg,[5,5,6])
    assert "methane_per_kg" not in df.columns

def test_formula_functions_and_where():
    df=pd.DataFrame({"x":[-1.,0.,4.]})
    got=evaluate_phenotype_formula(df,"where(x > 0, sqrt(x), 0)")
    assert np.allclose(got,[0,0,2])

def test_formula_rejects_python_execution():
    df=pd.DataFrame({"x":[1,2]})
    with pytest.raises(FormulaError):
        evaluate_phenotype_formula(df,"__import__('os').system('whoami')")

def test_formula_prevents_overwrite():
    df=pd.DataFrame({"x":[1,2]})
    with pytest.raises(FormulaError):
        create_derived_phenotype(df,"x","x * 2")

def test_round_classification_and_persistence():
    df=pd.DataFrame({
        "AnimalID":["A","B","C","D","A","B","C","D"],
        "Round":["R1"]*4+["R2"]*4,
        "methane":[1,2,8,9,1,3,7,10]
    })
    assignments, thresholds=classify_emitters_by_round(df,"AnimalID","Round","methane",25)
    assert len(assignments)==8
    assert list(thresholds["round"])==["R1","R2"]
    trans,persist=emitter_persistence_summary(assignments,"AnimalID","Round")
    assert not trans.empty
    assert persist.loc[persist.classification=="Consistently low","n_animals"].iloc[0] == 1
