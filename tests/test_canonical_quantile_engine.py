import numpy as np
import pandas as pd

from analysis_engine.advanced import fit_quantile_regression as canonical
from analysis_engine.advanced_research import fit_quantile_regression as compatibility_adapter


def test_advanced_research_adapter_uses_canonical_quantile_engine():
    rng = np.random.default_rng(17)
    x = np.linspace(0.5, 8.0, 100)
    y = 2.0 + 1.7 * x + rng.normal(0, 0.7, size=len(x))
    df = pd.DataFrame({"methane": y, "weight": x})

    expected = canonical(df, "methane", ["weight"], quantile=0.5)
    actual, used = compatibility_adapter(df, "methane", ["weight"], quantile=0.5)

    np.testing.assert_allclose(actual.params.to_numpy(), expected.params.to_numpy())
    assert len(used) == len(df)
    assert "methane" in used.columns


def test_quantile_engine_consumes_configured_quantile_when_not_overridden():
    rng = np.random.default_rng(23)
    x = np.linspace(1, 10, 120)
    df = pd.DataFrame({"methane": 3 + 2*x + rng.standard_t(3, len(x)), "weight": x})
    settings = {"conventional": {"quantile": 0.75}}
    model = canonical(df, "methane", ["weight"], settings=settings)
    assert model.q == 0.75
