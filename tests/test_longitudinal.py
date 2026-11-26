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


def _simulated_longitudinal_data(seed=31):
    import numpy as np
    rng = np.random.default_rng(seed)
    rows = []
    for animal in range(24):
        treatment = 'Control' if animal < 12 else 'Supplement'
        intercept = rng.normal(0, 1.0)
        slope = 0.12 + (0.10 if treatment == 'Supplement' else 0) + rng.normal(0, 0.025)
        occasions = [0, 1, 2, 4] if animal % 3 else [0, 2, 4]
        for time in occasions:
            rows.append({'animal': f'A{animal:02d}', 'day': time,
                         'treatment': treatment,
                         'methane': 20 + intercept + slope * time + rng.normal(0, .25),
                         'weight': 40 + animal * .2})
    return pd.DataFrame(rows)


def test_prepare_longitudinal_frame_retains_unbalanced_observations_and_audits_missing():
    from analysis_engine.longitudinal import prepare_longitudinal_frame
    data = _simulated_longitudinal_data()
    data.loc[0, 'methane'] = None
    used, audit = prepare_longitudinal_frame(data, 'methane', 'day', 'animal', ['weight'], 'treatment')
    assert used['_subject'].nunique() == 24
    assert audit['dropped_records'] == 1
    assert audit['subjects_with_unequal_visit_counts'] > 0
    assert audit['subjects_with_irregular_spacing'] > 0


def test_longitudinal_mixed_model_random_slope_predictions_and_diagnostics():
    from analysis_engine.longitudinal import (fit_longitudinal_mixed_model,
        longitudinal_prediction_frame, longitudinal_residual_diagnostics)
    data = _simulated_longitudinal_data()
    model, used, audit = fit_longitudinal_mixed_model(
        data, 'methane', 'day', 'animal', ['weight'], 'treatment',
        time_form='linear', random_slope=True, reml=False)
    assert audit['subjects'] == 24
    assert audit['treatment_interaction'] is True
    pred = longitudinal_prediction_frame(model, used, n_points=20, treatment_col='treatment')
    assert pred['treatment'].nunique() == 2
    assert {'predicted', 'ci_lower', 'ci_upper'}.issubset(pred.columns)
    assert (pred['ci_lower'] <= pred['predicted']).all()
    diag, summary = longitudinal_residual_diagnostics(model, used)
    assert len(diag) == len(used)
    assert summary['n_residuals'] == len(used)


def test_longitudinal_spline_time_model_fits():
    from analysis_engine.longitudinal import fit_longitudinal_mixed_model
    data = _simulated_longitudinal_data()
    model, used, audit = fit_longitudinal_mixed_model(
        data, 'methane', 'day', 'animal', treatment_col='treatment',
        time_form='spline', spline_df=3, random_slope=False, reml=False)
    assert len(used) > 50
    assert audit['time_form'] == 'spline'
    assert model is not None


def test_prepare_longitudinal_frame_converts_dates_to_elapsed_days():
    from analysis_engine.longitudinal import prepare_longitudinal_frame
    data = _simulated_longitudinal_data()
    origin = pd.Timestamp('2026-01-01')
    data['date'] = origin + pd.to_timedelta(data['day'], unit='D')
    used, audit = prepare_longitudinal_frame(data, 'methane', 'date', 'animal', time_kind='date')
    assert used['_time_numeric'].min() == 0
    assert used['_time_numeric'].max() == 4
    assert 'Elapsed days' in audit['time_label']


def test_longitudinal_frame_requires_repeated_subjects():
    from analysis_engine.longitudinal import prepare_longitudinal_frame
    data = pd.DataFrame({'animal': [f'A{i}' for i in range(8)], 'day': [1] * 8, 'y': range(8)})
    with pytest.raises(ValueError, match='at least two distinct time points'):
        prepare_longitudinal_frame(data, 'y', 'day', 'animal')


def test_longitudinal_model_comparison_reports_information_criteria_without_invalid_lrt():
    from analysis_engine.longitudinal import fit_longitudinal_mixed_model, compare_longitudinal_models
    data = _simulated_longitudinal_data(seed=53)
    intercept, _, _ = fit_longitudinal_mixed_model(
        data, 'methane', 'day', 'animal', treatment_col='treatment', random_slope=False, reml=False)
    slope, _, _ = fit_longitudinal_mixed_model(
        data, 'methane', 'day', 'animal', treatment_col='treatment', random_slope=True, reml=False)
    table, result = compare_longitudinal_models(intercept, slope, same_data=True, nested=False)
    assert table['aic'].notna().all()
    assert table['bic'].notna().all()
    assert pd.isna(result['p_value'])
    assert 'boundary' in result['note'] or 'AIC/BIC' in result['note']


def test_longitudinal_model_rejects_overlapping_outcome_time_subject_columns():
    from analysis_engine.longitudinal import prepare_longitudinal_frame
    data = _simulated_longitudinal_data()
    with pytest.raises(ValueError, match='three different columns'):
        prepare_longitudinal_frame(data, 'day', 'day', 'animal')
