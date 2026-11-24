import io, zipfile
import numpy as np
import pandas as pd
from analysis_engine.publication import publication_tables, build_publication_bundle

def sample():
    rng=np.random.default_rng(17); rows=[]
    for i in range(24):
        base=rng.normal(10,2)
        for visit in range(2):
            rows.append({"AnimalID":f"A{i:02}","Round":f"R{visit+1}","Breed":"Bonga" if i%2 else "Menz",
                         "methane":base+rng.normal(0,.5),"weight":20+i/3})
    return pd.DataFrame(rows)

def test_publication_tables_use_animal_as_independent_unit():
    out=publication_tables(sample(),"methane","AnimalID","Breed",["weight"])
    assert out["analysis_n"]==24
    assert "mean" in out["outcome_summary"]
    assert len(out["group_summary"])==2
    assert not out["spearman_correlations"].empty

def test_publication_bundle_contains_expected_reproducibility_outputs():
    raw=build_publication_bundle(sample(),outcome="methane",animal_id="AnimalID",group_col="Breed",
        covariates=["weight"],dataset_name="synthetic",study_species="sheep")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=set(z.namelist())
        assert "manifest.json" in names
        assert "README_REPORT.md" in names
        assert "tables/publication_tables.xlsx" in names
        assert "figures/outcome_distribution.html" in names
        assert "reproducibility/reproduce_report.py" in names

def test_publication_rejects_invalid_outcome():
    try: publication_tables(sample(),"not_a_column")
    except ValueError: return
    assert False, "Expected ValueError"
