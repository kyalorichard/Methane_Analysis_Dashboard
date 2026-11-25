import numpy as np
import pandas as pd
import pytest
from analysis_engine.time_series_forecasting import prepare_series, compare_forecasters


def test_prepare_series_aggregates_repeated_records_by_week():
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    df = pd.DataFrame({'date': list(dates) * 2,
                       'animal': ['A'] * 100 + ['B'] * 100,
                       'ch4': np.r_[np.arange(100), np.arange(100) + 2]})
    series = prepare_series(df, 'date', 'ch4', 'W', 'animal', 'All animals (aggregate)', 'mean')
    assert len(series) >= 3
    assert np.isfinite(series.dropna()).all()


def test_prepare_series_rejects_sparse_cross_sectional_data():
    df = pd.DataFrame({'date': pd.date_range('2024-01-01', periods=5, freq='D'), 'ch4': range(5)})
    with pytest.raises(ValueError, match='at least 12'):
        prepare_series(df, 'date', 'ch4', 'D')


def test_arima_chronological_holdout_and_future_forecast():
    idx = pd.date_range('2023-01-01', periods=36, freq='W')
    y = 10 + 0.1 * np.arange(36) + np.sin(np.arange(36) / 3)
    series = pd.Series(y, index=idx)
    result = compare_forecasters(series, ['ARIMA'], test_fraction=.2,
                                 arima_order=(1, 1, 1), future_periods=3, frequency='W')
    row = result['metrics'].iloc[0]
    assert row['status'] == 'completed'
    assert row['n_test'] >= 2
    assert len(result['predictions']['ARIMA']) == row['n_test']
    assert len(result['future']['ARIMA']) == 3


def test_expanded_forecasters_include_baselines_sarima_and_svr():
    idx = pd.date_range('2024-01-07', periods=60, freq='W')
    y = 10 + 0.15*np.arange(60) + 2*np.sin(2*np.pi*np.arange(60)/4)
    series = pd.Series(y, index=idx)
    result = compare_forecasters(
        series, ['Naive', 'Seasonal Naive', 'SARIMA', 'SVR'],
        test_fraction=.2, arima_order=(1,1,1), seasonal_order=(1,0,1,4),
        future_periods=4, frequency='W', seasonal_period=4, svr_lags=6
    )
    metrics = result['metrics'].set_index('model')
    for model in ['Naive', 'Seasonal Naive', 'SARIMA', 'SVR']:
        assert metrics.loc[model, 'status'] == 'completed'
        assert metrics.loc[model, 'n_test'] == 12
        assert len(result['predictions'][model]) == 12
        assert len(result['future'][model]) == 4


def test_forecaster_preserves_missing_time_bins_in_holdout():
    import numpy as np
    import pandas as pd
    from analysis_engine.time_series_forecasting import compare_forecasters
    idx = pd.date_range("2020-01-05", periods=30, freq="W")
    values = np.linspace(10, 20, 30)
    values[8] = np.nan
    values[25] = np.nan
    series = pd.Series(values, index=idx)
    result = compare_forecasters(series, models=["Naive"], test_fraction=0.2, future_periods=2, frequency="W")
    assert len(result["actual"]) == 6
    assert result["actual"].index.equals(idx[-6:])
    assert result["metrics"].iloc[0]["n_test"] == 5
