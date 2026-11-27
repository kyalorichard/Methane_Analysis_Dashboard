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
