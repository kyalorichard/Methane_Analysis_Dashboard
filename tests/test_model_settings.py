import numpy as np
import pandas as pd
from analysis_engine.model_comparison import compare_grouped_models, _pipeline, ML_MODELS


def test_comparison_accepts_user_hyperparameters_and_preprocessing():
    rng = np.random.default_rng(71)
    rows = []
    for group in range(10):
        for rep in range(4):
            x = float(rng.normal())
            rows.append({"animal": f"A{group}", "x": x,
                         "breed": "B1" if group % 2 else "B2",
                         "methane": 3.0 * x + group * 0.05 + rng.normal(0, .1)})
    frame = pd.DataFrame(rows)
    frame.loc[0, "x"] = np.nan
    result = compare_grouped_models(
        frame, "methane", ["x", "breed"], "animal",
        selected_models=["OLS (linear regression)", "Random Forest"],
        n_splits=3, n_boot=30, random_state=17,
        model_parameters={"Random Forest": {"n_estimators": 15, "max_depth": 3,
                                              "min_samples_leaf": 1}},
        preprocessing={"numeric_imputation": "mean",
                       "categorical_imputation": "constant",
                       "scale_numeric": False})
    assert set(result["metrics"].status) == {"completed"}
    assert result["oof_predictions"].shape[0] == len(frame)
    assert result["folds"] == 3


def test_settings_parameter_names_match_estimators():
    for name in ["Random Forest", "Extra Trees", "HistGradientBoosting", "SVR", "KNN"]:
        assert ML_MODELS[name].get_params(deep=False)
