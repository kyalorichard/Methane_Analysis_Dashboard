import numpy as np
import pandas as pd
import pytest
from analysis_engine.advanced_research import (
    fit_spline_additive, fit_random_intercept_model, animal_trajectory_slopes,
    multivariate_trait_associations, regression_prediction_diagnostics,
    variance_components_mixedlm,
)

@pytest.fixture
def research_data():
    rng = np.random.default_rng(71)
    animals = np.repeat([f"A{i:02d}" for i in range(24)], 4)
    time = np.tile(np.arange(4), 24)
    weight = rng.normal(45, 8, len(animals))
    animal_effect = {a: rng.normal(0, 1.5) for a in np.unique(animals)}
    methane = 8 + 0.08 * weight + 0.25 * time + np.array([animal_effect[a] for a in animals]) + rng.normal(0, .5, len(animals))
    return pd.DataFrame({"animal": animals, "time": time, "weight": weight,
                         "methane": methane, "co2": methane * .7 + rng.normal(0, .3, len(animals)),
                         "breed": np.where(np.arange(len(animals)) % 2, "B", "A")})


def test_spline_additive_model_runs(research_data):
    model, used = fit_spline_additive(research_data, "methane", ["weight"], ["breed"], 4)
    assert len(used) == len(research_data)
    assert np.isfinite(model.rsquared)


def test_mixed_model_and_variance_components(research_data):
    model, used = fit_random_intercept_model(research_data, "methane", ["weight", "time"], "animal")
    components = variance_components_mixedlm(model)
    assert len(used) == len(research_data)
    assert np.isclose(components.proportion_total.sum(), 1.0)


def test_animal_slopes(research_data):
    slopes = animal_trajectory_slopes(research_data, "animal", "time", "methane", 3)
    assert len(slopes) == 24
    assert "p_fdr_bh" in slopes


def test_multitrait_associations(research_data):
    result = multivariate_trait_associations(research_data, ["methane", "co2", "weight"])
    assert len(result) == 3
    assert result.p_fdr_bh.between(0, 1).all()


def test_prediction_diagnostics(research_data):
    result = regression_prediction_diagnostics(research_data.methane, research_data.methane + .2)
    assert result["n"] == len(research_data)
    assert result["mae"] == pytest.approx(.2)
