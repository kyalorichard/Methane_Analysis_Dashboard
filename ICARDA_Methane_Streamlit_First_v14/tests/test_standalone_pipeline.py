import io, zipfile
import numpy as np
import pandas as pd
from analysis_engine.standalone_pipeline import run_integrated_analysis, build_analysis_bundle, dataset_audit


def synthetic():
    rng=np.random.default_rng(12)
    rows=[]
    for i in range(40):
        weight=float(rng.normal(25,4))
        breed="A" if i<20 else "B"
        animal_effect=rng.normal(0,1)
        for visit in ["R1","R2"]:
            rows.append({"AnimalID":f"A{i:03d}","Round":visit,"Breed":breed,
                         "weight":weight,"mean_methane":12+0.2*weight+animal_effect+rng.normal(0,.5)})
    return pd.DataFrame(rows)


def test_integrated_pipeline_outputs_core_tables():
    d=synthetic()
    result=run_integrated_analysis(d,outcome="mean_methane",animal_id="AnimalID",
                                   session_col="Round",group_col="Breed",covariates=["weight"])
    assert "quality_control" in result["tables"]
    assert "data_dictionary" in result["tables"]
    assert "group_profile" in result["tables"]
    assert "repeatability" in result["summary"]
    assert result["manifest"]["audit"]["n_animals"]==40


def test_integrated_pipeline_grouped_ml():
    d=synthetic()
    result=run_integrated_analysis(d,outcome="mean_methane",animal_id="AnimalID",
        ml_features=["weight"],ml_models=["Ridge","Random Forest"],run_ml=True)
    assert result["summary"]["ml_status"].startswith("Completed")
    assert "ml_benchmark" in result["tables"]


def test_integrated_pipeline_blocks_ml_without_animal_id():
    d=synthetic()
    result=run_integrated_analysis(d,outcome="mean_methane",animal_id=None,
                                   ml_features=["weight"],run_ml=True)
    assert "Not run" in result["summary"]["ml_status"]


def test_export_bundle_is_portable_zip():
    d=synthetic()
    result=run_integrated_analysis(d,outcome="mean_methane",animal_id="AnimalID")
    payload=build_analysis_bundle(result,d)
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        names=set(z.namelist())
        assert "analysis_results.xlsx" in names
        assert "manifest.json" in names
        assert "report.html" in names
        assert "data/analysis_dataset.csv" in names


def test_dataset_audit_flags_duplicate_rows():
    d=synthetic()
    d=pd.concat([d,d.iloc[[0]]],ignore_index=True)
    _,qc,audit=dataset_audit(d,"AnimalID")
    assert audit["duplicate_rows"]==1
    assert qc.loc[qc["check"]=="Exact duplicate rows","status"].iloc[0]=="REVIEW"
