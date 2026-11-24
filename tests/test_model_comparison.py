import numpy as np
import pandas as pd
import pytest
from analysis_engine.model_comparison import compare_grouped_models


def make_data(seed=9):
    rng=np.random.default_rng(seed); rows=[]
    for g in range(12):
        animal=f'A{g}'
        weight=rng.normal(45,5)
        for rep in range(3):
            x=weight+rng.normal(0,1)
            rows.append({"animal":animal,"weight":x,"age":rng.uniform(1,5),
                         "breed":"A" if g%2 else "B",
                         "methane":18+0.35*x+0.7*rep+rng.normal(0,1)})
    return pd.DataFrame(rows)


def test_matched_comparison_returns_metrics_oof_and_pairwise():
    d=make_data()
    out=compare_grouped_models(d,"methane",["weight","age","breed"],"animal",
        selected_models=["OLS (linear regression)","Random Forest"],n_splits=3,n_boot=30)
    assert set(out["metrics"].model)=={"OLS (linear regression)","Random Forest"}
    assert out["metrics"].status.eq("completed").all()
    assert len(out["oof_predictions"])==len(d)
    assert len(out["paired_comparisons"])==1
    assert out["paired_comparisons"].iloc[0].bootstrap_replicates==30


def test_rejects_too_few_groups():
    d=make_data(); d["animal"]="one"
    with pytest.raises(ValueError,match="five independent groups"):
        compare_grouped_models(d,"methane",["weight"],"animal",selected_models=["OLS (linear regression)","Random Forest"])


def test_allometric_requires_one_numeric_positive_predictor():
    d=make_data()
    out=compare_grouped_models(d,"methane",["weight"],"animal",
        selected_models=["OLS (linear regression)","Allometric power-law regression"],n_splits=3,n_boot=20)
    assert out["metrics"].query("model == 'Allometric power-law regression'").iloc[0].status=="completed"


def test_nested_grouped_hyperparameter_tuning_uses_inner_group_cv():
    d=make_data(seed=29)
    out=compare_grouped_models(d,"methane",["weight","age"],"animal",
        selected_models=["OLS (linear regression)","Random Forest"],
        n_splits=3,n_boot=20,random_state=13,tune_models=True,tuning_iter=2)
    assert out["metrics"].status.eq("completed").all()
    assert len(out["tuned_parameters"]["Random Forest"])==3
    assert all("model__n_estimators" in fold for fold in out["tuned_parameters"]["Random Forest"])


def test_grid_search_is_nested_with_grouped_outer_validation():
    d=make_data(seed=37)
    out=compare_grouped_models(d,"methane",["weight","age"],"animal",
        selected_models=["OLS (linear regression)","KNN"],n_splits=3,n_boot=10,
        tuning_method="grid",tune_models=True)
    assert out["metrics"].status.eq("completed").all()
    assert len(out["tuned_parameters"]["KNN"])==3
