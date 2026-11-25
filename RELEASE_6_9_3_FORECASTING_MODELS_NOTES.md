# Release 6.9.3 — Time-Series Forecasting Models

## Added
- New Time-Series Forecasting page under Longitudinal & Multi-Study.
- ARIMA forecasting using statsmodels (already part of base requirements).
- Prophet forecasting with optional `prophet` dependency.
- LSTM forecasting using PyTorch with optional `torch` dependency.
- Existing Support Vector Regression (SVR) remains available in ML Benchmarking for continuous methane outcomes.
- Select a methane outcome, date/time variable, population aggregate or individual animal series, temporal frequency, within-period aggregation, chronological holdout fraction, ARIMA order, LSTM lookback and training epochs.
- Holdout evaluation uses the final chronological segment; forecasts are not evaluated with random row-wise splits.
- Exports for holdout metrics and future forecasts.

## Scientific constraints
- Forecasting requires repeated measurements with adequate temporal density. Cross-sectional single-measurement data are not forecastable as an individual time series.
- Repeated animal records are either filtered to one animal or aggregated by time period for a population-level series. The aggregation choice changes the estimand and must be reported.
- Missing time bins are regularised and training gaps are interpolated using training-history values. Holdout actuals are not imputed for scoring.
- ARIMA/Prophet/LSTM are univariate time-series baselines in this release. They do not yet use exogenous covariates or panel/global multi-animal sequence models.
- Chronological holdout is a first evaluation layer. Rolling-origin validation and independent temporal/farm validation are recommended for publication-grade forecasting.
- Forecasts are predictions of the selected recorded phenotype. They are not automatically calibrated methane mass-flux estimates.

## Optional installation
`pip install -r requirements-forecasting-optional.txt`

ARIMA is available from the base `statsmodels` dependency. Prophet and LSTM are enabled only when their optional packages are installed.

## Verification
- Python compilation checks passed for new forecasting engine, page and navigation module.
- Synthetic weekly time-series smoke test completed for ARIMA and LSTM; holdout predictions and four-step future forecasts were returned.
- Full existing test suite: 91 passed, 2 failed solely because PyArrow is absent in the test environment (both failures are existing Parquet I/O tests).
- Prophet runtime test was not performed because Prophet is not installed in this environment.
- Streamlit browser/deployment test was not performed.
