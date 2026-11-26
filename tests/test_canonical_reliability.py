import numpy as np
import pytest
import pandas as pd

from analysis_engine.reliability import (
    build_subject_occasion_panel,
    estimate_balanced_panel_icc,
    estimate_long_format_icc1,
    bland_altman_paired,
)
from analysis_engine.service_registry import get_service


def repeated_data(seed=17):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(30):
        base = rng.normal(10, 2)
        for round_id in ("R1", "R2", "R3"):
            rows.append({"animal": f"A{i}", "round": round_id, "methane": base + rng.normal(0, .5)})
    return pd.DataFrame(rows)


def test_panel_builder_is_canonical_and_audits_duplicate_cells():
    df = pd.DataFrame({
        "animal": ["A", "A", "A", "B", "B"],
        "round": ["R1", "R1", "R2", "R1", "R2"],
        "y": [1.0, 3.0, 2.0, 4.0, 5.0],
    })
    panel, audit = build_subject_occasion_panel(df, "animal", "round", "y", "median")
    assert panel.loc["A", "R1"] == 2.0
    assert audit["duplicate_subject_occasion_rows_aggregated"] == 1
    assert audit["n_complete_subjects"] == 2


def test_legacy_balanced_icc_wrapper_routes_to_canonical_engine():
    from analysis_engine.research_methods import estimate_repeatability_icc
    rng = np.random.default_rng(4)
    base = rng.normal(size=40)
    panel = pd.DataFrame({f"r{i}": base + rng.normal(scale=.25, size=40) for i in range(3)})
    expected = estimate_balanced_panel_icc(panel, model="ICC3", n_boot=250, random_state=9)
    actual = estimate_repeatability_icc(panel, model="ICC3", n_boot=250, random_state=9)
    assert actual == expected
    assert get_service("repeatability_balanced_panel") is estimate_balanced_panel_icc


def test_long_format_icc_legacy_wrapper_routes_to_canonical_engine():
    from analysis_engine.advanced import repeatability_icc
    df = repeated_data()
    expected = estimate_long_format_icc1(df, "animal", "methane")
    actual = repeatability_icc(df, "animal", "methane")
    assert actual == expected
    assert get_service("repeatability_long_format") is estimate_long_format_icc1


def test_bland_altman_compatibility_wrapper_uses_canonical_paired_engine():
    from analysis_engine.research_methods import bland_altman_summary
    rng = np.random.default_rng(2)
    a = rng.normal(10, 1, 50)
    b = a + .4 + rng.normal(0, .2, 50)
    pairs, canonical = bland_altman_paired(a, b, n_boot=250, random_state=5)
    wrapped = bland_altman_summary(a, b, n_boot=250, random_state=5)
    assert len(pairs) == 50
    assert wrapped == canonical


def test_advanced_long_format_bland_altman_uses_canonical_engine():
    from analysis_engine.advanced import bland_altman
    df = repeated_data()
    pairs, result = bland_altman(df, "animal", "methane", "round", "R1", "R2")
    assert len(pairs) >= 10
    assert {"animal_mean", "difference_b_minus_a"}.issubset(pairs.columns)
    assert "loa_lower" in result and "loa_upper" in result


def test_local_workspace_preserves_original_source_bytes(tmp_path, monkeypatch):
    from platform_core import local_workspace

    monkeypatch.setenv("METHANE_METADATA_DB", str(tmp_path / "metadata.sqlite3"))
    monkeypatch.setattr(local_workspace, "ROOT", tmp_path / "workspace")
    monkeypatch.setattr(local_workspace, "dataframe_to_parquet_bytes", lambda *a, **k: b"canonical-parquet-fixture")
    project_id = local_workspace.create_project("tenant-test", "researcher", "Test project", "sheep")
    original = b"animal_id,methane\nA1,12.3\nA2,14.1\n"
    df = pd.DataFrame({"animal_id": ["A1", "A2"], "methane": [12.3, 14.1]})
    saved = local_workspace.save_dataset("tenant-test", "researcher", project_id, "study.csv", original, df, "sheep")
    recovered, filename, source_format = local_workspace.load_raw_source(
        "tenant-test", project_id, saved["id"], "researcher"
    )
    assert recovered == original
    assert filename == "study.csv"
    assert source_format == "csv"
    assert saved["original_source_retained"] is True


def test_legacy_repeatability_page_no_longer_implements_its_own_icc():
    from pathlib import Path
    page = Path(__file__).resolve().parents[1] / "pages" / "07_Repeatability_Reliability.py"
    source = page.read_text()
    assert "build_reliability_panel" in source
    assert "ms_between" not in source.lower()
    assert "exploratory icc(1,1)" not in source.lower()


def test_group_comparison_page_uses_canonical_service():
    from pathlib import Path
    page = Path(__file__).resolve().parents[1] / "pages" / "08_Group_Comparisons.py"
    source = page.read_text()
    assert 'get_service("group_comparison")' in source
    assert "groupby([animal_col, group]" in source


def test_mixed_model_icc_reports_variance_components_and_cluster_bootstrap():
    from analysis_engine.reliability import estimate_mixed_model_icc

    rng = np.random.default_rng(2026)
    rows = []
    for i in range(18):
        animal_effect = rng.normal(0, 2.0)
        for j in range(2 + (i % 3)):
            rows.append({
                "animal": f"A{i}",
                "occasion": f"R{j % 2 + 1}",
                "methane": 20 + animal_effect + (j % 2) * 0.8 + rng.normal(0, 0.7),
            })
    result = estimate_mixed_model_icc(
        pd.DataFrame(rows), "animal", "methane", "occasion",
        n_boot=50, random_state=19,
    )
    assert result["n_subjects"] == 18
    assert result["n_records"] == len(rows)
    assert 0 <= result["icc"] <= 1
    assert result["icc_ci_low"] <= result["icc_ci_high"]
    assert result["subject_variance"] >= 0
    assert result["residual_variance"] > 0
    assert result["occasion_adjustment"] == "Fixed effect: occasion"


def test_mixed_model_icc_requires_repeated_subjects():
    from analysis_engine.reliability import estimate_mixed_model_icc

    df = pd.DataFrame({"animal": [f"A{i}" for i in range(8)], "y": np.arange(8, dtype=float)})
    with pytest.raises(ValueError, match="repeated observations"):
        estimate_mixed_model_icc(df, "animal", "y", n_boot=50)
