import numpy as np
import pandas as pd

from analysis_engine.data_provenance import dataframe_fingerprint
from analysis_engine.quality_control import flag_data_quality_rows, configured_range_summary
from analysis_engine.research_intelligence import dataframe_fingerprint as intelligence_fingerprint
from analysis_engine.research_intelligence import flag_data_quality
from analysis_engine.research_hardening import configurable_qc
from analysis_engine.service_registry import get_service, service_names
from analysis_engine.emitter_thresholds import assign_emitter_tails


def test_all_fingerprint_consumers_use_same_canonical_algorithm():
    frame = pd.DataFrame({"animal": ["A", "B", "A"], "methane": [1.2, 2.4, 1.5]})
    expected = dataframe_fingerprint(frame)
    assert intelligence_fingerprint(frame) == expected
    assert get_service("dataframe_fingerprint")(frame) == expected
    assert dataframe_fingerprint(frame.copy()) == expected
    assert dataframe_fingerprint(frame.iloc[::-1].reset_index(drop=True)) != expected


def test_row_level_qc_is_central_non_destructive_and_adapter_compatible():
    frame = pd.DataFrame({"methane": [1.0, 2.0, 3.0, 100.0, np.nan],
                          "duration": [60, 60, 60, 20, 60]})
    before = frame.copy(deep=True)
    central = flag_data_quality_rows(frame, ["methane"], "duration", 30,
                                     nonnegative_columns=["methane"])
    adapter = flag_data_quality(frame, ["methane"], "duration", 30,
                                nonnegative_columns=["methane"])
    assert len(central) == len(adapter)
    assert "row_position" in central.columns
    assert central["flags"].str.contains("IQR outlier").any()
    assert central["flags"].str.contains("Below minimum recording duration").any()
    pd.testing.assert_frame_equal(frame, before)


def test_configured_qc_legacy_adapter_matches_central_summary():
    frame = pd.DataFrame({"x": [-1, 1, 2, 11, np.nan]})
    rules = {"x": {"min": 0, "max": 10, "source": "protocol"}}
    expected = configured_range_summary(frame, rules)
    actual = configurable_qc(frame, rules)
    pd.testing.assert_frame_equal(actual, expected)


def test_shared_services_are_registered():
    required = {"dataframe_fingerprint", "run_quality_control", "row_level_qc",
                "configured_range_summary", "apply_qc_disposition",
                "animal_random_intercept", "grouped_classification",
                "publication_bundle", "scientific_report"}
    assert required.issubset(set(service_names()))
    for name in required:
        assert callable(get_service(name))


def test_emitter_threshold_service_preserves_rank_based_tail_assignments():
    values = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    labels, percentiles, low, high = assign_emitter_tails(values, 20)
    assert (labels == "Low emitter").sum() == 2
    assert (labels == "High emitter").sum() == 2
    assert low == 2.8
    assert high == 8.2
    assert percentiles.iloc[0] == 10.0
