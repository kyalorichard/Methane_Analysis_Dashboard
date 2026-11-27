import pandas as pd
from analysis_engine.quality_control import run_quality_control, findings_frame, dataframe_fingerprint


def test_unified_qc_flags_missing_duplicates_outliers_and_custom_ranges():
    df = pd.DataFrame({
        "animal": ["a", "a", "b", "c", "c", "d"],
        "visit": [1, 1, 1, 1, 2, 1],
        "methane": [10.0, 10.0, 11.0, 12.0, 1000.0, 13.0],
        "weight": [20.0, 20.0, 22.0, 24.0, 25.0, None],
    })
    report = run_quality_control(df, rules={"methane": {"min": 0, "max": 100, "source": "protocol"}}, animal_id="animal", time_col="visit")
    checks = {x["check"] for x in report["findings"]}
    assert "Exact duplicate rows" in checks
    assert "Missingness" in checks
    assert "Configured study-specific range" in checks
    assert "Duplicate animal-time combinations" in checks
    assert report["dataset_fingerprint"] == dataframe_fingerprint(df)
    assert len(findings_frame(report)) == len(report["findings"])


def test_unified_qc_is_non_destructive_and_handles_empty_frame():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    before = df.copy(deep=True)
    run_quality_control(df)
    pd.testing.assert_frame_equal(df, before)
    empty = run_quality_control(pd.DataFrame())
    assert empty["blocking_issues"] is True
    assert empty["severity_counts"]["critical"] >= 1


def test_qc_repeated_measure_summary():
    df = pd.DataFrame({"animal": ["a", "a", "b", None], "round": [1, 2, 1, 1], "y": [1, 2, 3, 4]})
    report = run_quality_control(df, animal_id="animal", time_col="round")
    assert report["animal_repeated_measure_summary"]["n_animals"] == 2
    assert report["animal_repeated_measure_summary"]["repeated_animals"] == 1
    assert any(x["check"] == "Missing animal identifiers" for x in report["findings"])


def test_unified_qc_run_can_be_saved_to_scoped_registry(tmp_path):
    from platform_core import run_registry
    db = tmp_path / "qc_runs.sqlite3"
    run_registry.save_run(
        "qc-test-run", {"dataset_name": "study.csv", "dataset_fingerprint_sha256": "abc123"},
        {"qc_report": {"severity_counts": {"critical": 0}}}, status="completed",
        db_path=db, tenant_id="tenant-a", project_id="project-a", user_subject="user-a",
        module_key="unified_data_quality_qc",
    )
    rows = run_registry.list_runs(db_path=db, tenant_id="tenant-a", project_id="project-a", user_subject="user-a")
    assert len(rows) == 1
    assert rows[0]["module_key"] == "unified_data_quality_qc"
    assert rows[0]["dataset_fingerprint"] == "abc123"


def test_range_disposition_keep_and_drop_are_non_destructive():
    from analysis_engine.quality_control import apply_range_disposition
    df = pd.DataFrame({"animal": ["a", "a", "b"], "methane": [10.0, 999.0, 20.0]})
    before = df.copy(deep=True)
    kept, keep_audit = apply_range_disposition(df, variable="methane", row_positions=[1], action="keep")
    pd.testing.assert_frame_equal(kept, df)
    assert keep_audit["action"] == "keep"
    dropped, drop_audit = apply_range_disposition(df, variable="methane", row_positions=[1], action="drop")
    assert len(dropped) == 2
    assert 999.0 not in dropped["methane"].tolist()
    assert len(df) == 3
    pd.testing.assert_frame_equal(df, before)
    assert drop_audit["records_after"] == 2


def test_range_disposition_estimates_from_in_range_global_median():
    from analysis_engine.quality_control import apply_range_disposition
    df = pd.DataFrame({"x": [10.0, 999.0, 20.0, 30.0]})
    mask = (df["x"] < 0) | (df["x"] > 100)
    updated, audit = apply_range_disposition(df, variable="x", row_positions=[1], action="estimate",
                                             method="Global median", valid_mask=~mask)
    assert updated.loc[1, "x"] == 20.0
    assert audit["replacement_values"] == [20.0]
    assert df.loc[1, "x"] == 999.0


def test_range_disposition_estimates_group_median():
    from analysis_engine.quality_control import apply_range_disposition
    df = pd.DataFrame({"breed": ["A", "A", "B", "B"], "x": [10.0, 999.0, 20.0, 30.0]})
    mask = (df["x"] < 0) | (df["x"] > 100)
    updated, _ = apply_range_disposition(df, variable="x", row_positions=[1], action="estimate",
                                         method="Group median", group_col="breed", valid_mask=~mask)
    assert updated.loc[1, "x"] == 10.0


def test_range_disposition_interpolates_within_animal_without_extrapolation():
    from analysis_engine.quality_control import apply_range_disposition
    df = pd.DataFrame({"animal": ["A", "A", "A", "B", "B"],
                       "day": [1, 2, 3, 1, 2], "x": [10.0, 999.0, 30.0, 5.0, 999.0]})
    mask = (df["x"] < 0) | (df["x"] > 100)
    updated, _ = apply_range_disposition(df, variable="x", row_positions=[1], action="estimate",
                                         method="Within-animal interpolation", animal_id="animal",
                                         time_col="day", valid_mask=~mask)
    assert updated.loc[1, "x"] == 20.0
    assert df.loc[1, "x"] == 999.0


def test_range_disposition_fails_when_group_has_no_valid_donor():
    import pytest
    from analysis_engine.quality_control import apply_range_disposition
    df = pd.DataFrame({"group": ["A", "A"], "x": [999.0, 1000.0]})
    mask = (df["x"] < 0) | (df["x"] > 100)
    with pytest.raises(ValueError, match="Could not estimate"):
        apply_range_disposition(df, variable="x", row_positions=[0], action="estimate",
                                method="Group median", group_col="group", valid_mask=~mask)


def test_configured_range_mask_flags_only_values_outside_inclusive_limits():
    from analysis_engine.quality_control import configured_range_mask
    df = pd.DataFrame({"x": [-1.0, 0.0, 5.0, 10.0, 11.0, None]})
    mask = configured_range_mask(df, "x", {"min": 0, "max": 10})
    assert mask.tolist() == [True, False, False, False, True, False]


def test_interpolation_refuses_to_extrapolate_outside_in_range_visits():
    import pytest
    from analysis_engine.quality_control import apply_range_disposition
    df = pd.DataFrame({"animal": ["A", "A"], "day": [1, 2], "x": [10.0, 999.0]})
    mask = (df["x"] < 0) | (df["x"] > 100)
    with pytest.raises(ValueError, match="Could not estimate"):
        apply_range_disposition(df, variable="x", row_positions=[1], action="estimate",
                                method="Within-animal interpolation", animal_id="animal",
                                time_col="day", valid_mask=~mask)


def test_range_disposition_winsorizes_selected_values_using_valid_donor_quantiles():
    from analysis_engine.quality_control import apply_range_disposition
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 1000.0]})
    before = df.copy(deep=True)
    mask = (df["x"] < 0) | (df["x"] > 100)
    updated, audit = apply_range_disposition(
        df, variable="x", row_positions=[4], action="winsorize",
        valid_mask=~mask, lower_quantile=0.05, upper_quantile=0.95,
    )
    assert abs(updated.loc[4, "x"] - 3.85) < 1e-10
    assert audit["action"] == "winsorize"
    assert abs(audit["lower_bound"] - 1.15) < 1e-10
    assert abs(audit["upper_bound"] - 3.85) < 1e-10
    pd.testing.assert_frame_equal(df, before)


def test_winsorization_rejects_invalid_quantiles_and_insufficient_donors():
    import pytest
    from analysis_engine.quality_control import apply_range_disposition
    df = pd.DataFrame({"x": [999.0, 1000.0, 10.0]})
    with pytest.raises(ValueError, match="quantiles"):
        apply_range_disposition(df, variable="x", row_positions=[0], action="winsorize",
                                lower_quantile=0.95, upper_quantile=0.05)
    with pytest.raises(ValueError, match="At least two"):
        apply_range_disposition(df, variable="x", row_positions=[0, 1], action="winsorize",
                                valid_mask=pd.Series([False, False, True]))
