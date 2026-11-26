import numpy as np
import pandas as pd
import pytest

from analysis_engine.advanced_inference import (
    fit_population_average_gee, fit_cluster_robust_ols,
    missingness_audit, delta_adjusted_group_sensitivity,
    adjust_multiple_comparisons,
)


def _cluster_data(seed=44):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(32):
        group = "Control" if i < 16 else "Supplement"
        intercept = rng.normal(0, 1)
        for day in (0, 1, 2, 3):
            rows.append({"animal": f"A{i}", "group": group, "day": day,
                         "methane": 20 + intercept + .2 * day + (1.1 if group == "Supplement" else 0) + rng.normal(0, .4),
                         "weight": 40 + i * .1 + rng.normal(0, .2)})
    return pd.DataFrame(rows)


def test_gee_population_average_uses_cluster_robust_inference():
    result, used, audit = fit_population_average_gee(
        _cluster_data(), "methane", ["day", "group"], "animal", "exchangeable")
    assert audit["n_clusters"] == 32
    assert audit["n_records"] == 128
    assert "population-average" in audit["estimand"]
    assert "group" in result.params.index or any("group" in x for x in result.params.index)


def test_cluster_robust_ols_returns_cluster_adjusted_model():
    result, used, audit = fit_cluster_robust_ols(
        _cluster_data(), "methane", ["day", "group"], "animal")
    assert audit["n_clusters"] == 32
    assert "cluster" in result.cov_type


def test_gee_rejects_too_few_clusters():
    data = _cluster_data()
    data["animal"] = data["animal"].map(lambda x: x if x in {"A0", "A1", "A2", "A3"} else "A0")
    with pytest.raises(ValueError, match="five independent clusters"):
        fit_population_average_gee(data, "methane", ["day"], "animal")


def test_missingness_audit_reports_patterns_and_cluster_missingness():
    data = _cluster_data()
    data.loc[0:4, "methane"] = np.nan
    audit, patterns, clusters, summary = missingness_audit(data, ["methane", "weight"], "animal")
    assert audit.loc[audit.variable == "methane", "n_missing"].iloc[0] == 5
    assert patterns.n_records.sum() == len(data)
    assert clusters is not None
    assert summary["complete_case_records"] == len(data) - 5


def test_delta_sensitivity_changes_group_contrast_and_reports_missing_counts():
    data = _cluster_data()
    data.loc[(data.group == "Supplement") & (data.day == 3), "methane"] = np.nan
    table, audit = delta_adjusted_group_sensitivity(
        data, "methane", "group", "Control", "Supplement", deltas=(-1, 0, 1))
    assert table.loc[0, "missing_b"] == 16
    assert table.loc[2, "difference_a_minus_b"] < table.loc[0, "difference_a_minus_b"]
    assert "hypothetical MNAR" in audit["note"]


def test_multiple_testing_methods_preserve_missing_values_and_adjust():
    data = pd.DataFrame({"term": ["a", "b", "c"], "p_value": [.001, .02, np.nan]})
    out = adjust_multiple_comparisons(data, method="holm")
    assert out.loc[0, "p_adjusted"] == pytest.approx(.002)
    assert pd.isna(out.loc[2, "p_adjusted"])
    assert out["n_tests_adjusted"].iloc[0] == 2


def test_multiple_testing_rejects_invalid_p_values():
    with pytest.raises(ValueError, match="between zero and one"):
        adjust_multiple_comparisons(pd.DataFrame({"p_value": [1.2]}))
