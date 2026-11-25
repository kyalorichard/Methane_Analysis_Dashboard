# Release 6.9.4 — Expanded Time-Series Forecasting

## Models
- Naïve persistence benchmark.
- Seasonal-naïve benchmark with configurable season length.
- ARIMA non-seasonal statistical model.
- SARIMA seasonal statistical model using statsmodels SARIMAX.
- Prophet optional trend/seasonality model.
- SVR forecasting using lagged target values and standardised predictors, recursively forecast.
- LSTM sequence forecasting (optional PyTorch).

## Evaluation
- Chronological holdout only; no random row-wise shuffling.
- Common holdout metrics: MAE, RMSE, R² and test sample count.
- Future forecasts refit on the full available series.
- Naïve and seasonal-naïve models provide essential reference baselines.

## Limitations
- Models are univariate; no exogenous covariates or panel/global multi-animal sequence models.
- The seasonal period must be specified to match the data cadence and scientific cycle.
- SVR and LSTM future predictions are recursive and may accumulate error.
- Prediction intervals and rolling-origin backtesting are not yet included.
- Sparse or irregular time series may not be suitable; missing bins are interpolated in the training segment only for fitting.
- Forecasts refer to the selected measured phenotype, not automatically calibrated methane flux.

## Dependencies
- ARIMA/SARIMA: statsmodels (base requirements).
- SVR: scikit-learn (base requirements).
- Prophet and LSTM: optional dependencies in requirements-forecasting-optional.txt.
