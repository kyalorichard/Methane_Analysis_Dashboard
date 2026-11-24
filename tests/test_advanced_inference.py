import numpy as np
import pandas as pd
import pytest
from analysis_engine.advanced_research import (
    fit_quantile_regression, fit_allometric_scaling,
    cluster_bootstrap_mean_difference,
)

@pytest.fixture
def inference_data():
    rng = np.random.default_rng(902)
    animals = np.repeat([f"A{i:03d}" for i in range(60)], 3)
    group_by_animal = {a: ("control" if i < 30 else "treated") for i, a in enumerate(sorted(set(animals)))}
    group = np.array([group_by_animal[a] for a in animals])
    weight = rng.lognormal(3.5, 0.25, len(animals))
    animal_effect = {a: rng.normal(0, 0.7) for a in set(animals)}
    methane = 0.8 * weight ** 0.75 * np.exp(np.array([animal_effect[a] for a in animals]) * .1 + rng.normal(0, .08, len(animals)))
    methane += (group == "treated") * 1.2
    return pd.DataFrame({"animal": animals, "group": group, "weight": weight, "methane": methane})


def test_quantile_regression(inference_data):
    model, used = fit_quantile_regression(inference_data, "methane", ["weight", "group"], .5)
    assert len(used) == len(inference_data)
    assert np.isfinite(model.params).all()


def test_allometric_scaling(inference_data):
    result = fit_allometric_scaling(inference_data, "methane", "weight")
    assert result["n"] == len(inference_data)
    assert result["exponent_ci_low"] < result["exponent_ci_high"]


def test_animal_cluster_bootstrap_is_deterministic(inference_data):
    a = cluster_bootstrap_mean_difference(inference_data, "methane", "group", "treated", "control", "animal", 300, seed=44)
    b = cluster_bootstrap_mean_difference(inference_data, "methane", "group", "treated", "control", "animal", 300, seed=44)
    assert a["n_animals_a"] == 30
    assert a["n_animals_b"] == 30
    assert a["difference_a_minus_b"] == pytest.approx(b["difference_a_minus_b"])
    assert a["ci_low"] == pytest.approx(b["ci_low"])


def test_allometric_rejects_nonpositive_values():
    with pytest.raises(ValueError):
        fit_allometric_scaling(pd.DataFrame({"y": [0, -1] * 6, "x": [1, 2] * 6}), "y", "x")
