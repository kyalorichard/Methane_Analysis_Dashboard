import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from analysis_engine.classification_validation import grouped_nested_classification, external_classification_validation


def make_data(seed=7):
    rng=np.random.default_rng(seed); rows=[]
    for g in range(36):
        latent=rng.normal()
        for rep in range(2):
            x=latent+rng.normal(0,.25)
            rows.append({"AnimalID":f"A{g}","x":x,"z":rng.normal(),"class":"High" if latent>0 else "Low"})
    return pd.DataFrame(rows)


def test_nested_grouped_classification_oof_and_calibration():
    d=make_data()
    scores, results, labels=grouped_nested_classification(d,"class",["x","z"],"AnimalID",
        models=["Logistic Regression"],outer_splits=3,inner_splits=2,calibration="sigmoid",tune=False)
    assert scores.iloc[0].status=="COMPLETE"
    r=results["Logistic Regression"]
    assert len(r["probabilities"])==len(d)
    p=r["probabilities"].filter(like="probability_").to_numpy()
    assert np.allclose(p.sum(axis=1),1,atol=1e-6)
    assert r["summary"]["log_loss"]>=0
    assert set(labels)=={"High","Low"}


def test_nested_grouped_classification_rejects_too_few_groups():
    d=make_data().iloc[:8]
    with pytest.raises(ValueError,match="five independent groups"):
        grouped_nested_classification(d,"class",["x"],"AnimalID",models=["Logistic Regression"])


def test_external_classification_uses_frozen_model():
    d=make_data(); y=(d["class"]=="High").astype(int)
    model=make_pipeline(SimpleImputer(),StandardScaler(),LogisticRegression()).fit(d[["x","z"]],y)
    ext=d.iloc[:12].copy(); ext["class"]=(ext["class"]=="High").astype(int)
    result=external_classification_validation(model,ext,"class",["x","z"],"AnimalID")
    assert result["n_records"]==12
    assert 0<=result["accuracy"]<=1
