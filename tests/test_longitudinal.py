import pandas as pd
import pytest

from analysis_engine.longitudinal import paired_round_changes


def test_paired_round_changes_calculates_comparison_minus_baseline():
    pivot = pd.DataFrame(
        {"Round 1": [10.0, 20.0, None], "Round 2": [13.0, 18.0, 30.0]},
        index=["A", "B", "C"],
    )
    result = paired_round_changes(pivot, "Round 1", "Round 2")
    assert result.index.tolist() == ["A", "B"]
    assert result["change"].tolist() == [3.0, -2.0]


def test_paired_round_changes_rejects_same_round():
    pivot = pd.DataFrame({"Round 1": [1.0]})
    with pytest.raises(ValueError, match="two different"):
        paired_round_changes(pivot, "Round 1", "Round 1")


def test_paired_round_changes_rejects_ambiguous_duplicate_round_label():
    pivot = pd.DataFrame([[1.0, 2.0], [3.0, 4.0]], columns=["Round 1", "Round 1"])
    with pytest.raises(ValueError, match="exactly one"):
        paired_round_changes(pivot, "Round 1", "Round 2")


def test_paired_round_changes_coerces_non_numeric_values_and_drops_incomplete_pairs():
    pivot = pd.DataFrame({"Round 1": ["1", "bad"], "Round 2": ["2", "3"]})
    result = paired_round_changes(pivot, "Round 1", "Round 2")
    assert len(result) == 1
    assert result["change"].iloc[0] == 1.0
