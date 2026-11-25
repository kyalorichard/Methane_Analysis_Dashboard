"""Chronological forecasting utilities for methane phenotype time series.

Forecasts a single regularly sampled series. The caller must aggregate repeated
animal records to the selected time frequency or select a single animal first.
"""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.svm import SVR
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def prepare_series(df: pd.DataFrame, date_col: str, target: str, frequency: str = "W",
                   animal_col: str | None = None, animal_value=None,
                   aggregation: str = "mean") -> pd.Series:
    required = [date_col, target] + ([animal_col] if animal_col else [])
    d = df[required].copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d[target] = pd.to_numeric(d[target], errors="coerce")
    d = d.dropna(subset=[date_col, target])
    if animal_col and animal_value not in (None, "All animals (aggregate)"):
        d = d.loc[d[animal_col].astype(str) == str(animal_value)]
    if d.empty:
        raise ValueError("No valid date/target observations remain after filtering.")
    d = d.set_index(date_col).sort_index()
    agg = "mean" if aggregation == "mean" else "median"
    s = d[target].resample(frequency).agg(agg).dropna().astype(float)
    if s.index.has_duplicates:
        s = s.groupby(level=0).mean()
    if len(s) < 12:
        raise ValueError(f"Only {len(s)} time points are available after resampling; at least 12 are required for this forecasting workflow.")
    # Regularise gaps to a continuous index; missing periods remain NaN and are
    # interpolated using past observations only for the training portion below.
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq=frequency)
    return s.reindex(full_idx)


def _metrics(actual, predicted):
    actual = np.asarray(actual, dtype=float); predicted = np.asarray(predicted, dtype=float)
    ok = np.isfinite(actual) & np.isfinite(predicted)
    if ok.sum() == 0:
        return {"n_test": 0, "mae": np.nan, "rmse": np.nan, "r2": np.nan}
    a, p = actual[ok], predicted[ok]
    return {"n_test": int(ok.sum()), "mae": float(mean_absolute_error(a, p)),
            "rmse": float(np.sqrt(mean_squared_error(a, p))),
            "r2": float(r2_score(a, p)) if len(a) > 1 else np.nan}


def _fit_arima(train, test, order):
    from statsmodels.tsa.arima.model import ARIMA
    model = ARIMA(train, order=order, enforce_stationarity=False, enforce_invertibility=False)
    fitted = model.fit()
    pred = fitted.forecast(steps=len(test))
    return np.asarray(pred, dtype=float), fitted


def _fit_prophet(train, test, future_periods, frequency):
    try:
        from prophet import Prophet
    except ImportError as exc:
        raise ImportError("Prophet is optional. Install it with `pip install prophet` to enable this model.") from exc
    clean_train = train.dropna()
    if len(clean_train) < 8:
        raise ValueError("Prophet requires at least eight observed training periods.")
    tr = pd.DataFrame({"ds": clean_train.index, "y": clean_train.values})
    model = Prophet(daily_seasonality=False, weekly_seasonality=(frequency in ("D", "W")),
                    yearly_seasonality=(len(train) >= 24), seasonality_mode="additive")
    model.fit(tr)
    test_frame = pd.DataFrame({"ds": test.index})
    pred_test = model.predict(test_frame)["yhat"].to_numpy() if len(test_frame) else np.array([])
    future = model.make_future_dataframe(periods=future_periods, freq=frequency, include_history=False)
    pred_future = model.predict(future)[["ds", "yhat"]]
    return pred_test, pred_future


def _fit_lstm(train, test, future_periods, lookback=6, epochs=80, hidden_size=32, seed=42):
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise ImportError("LSTM is optional. Install PyTorch (`pip install torch`) to enable this model.") from exc
    if len(train) <= lookback + 5:
        raise ValueError(f"LSTM requires more than {lookback + 5} training time points; got {len(train)}.")
    torch.manual_seed(int(seed)); np.random.seed(int(seed))
    mean = float(np.mean(train)); std = float(np.std(train)) or 1.0
    z = (np.asarray(train, dtype=np.float32) - mean) / std
    X, y = [], []
    for i in range(lookback, len(z)):
        X.append(z[i-lookback:i]); y.append(z[i])
    X = torch.tensor(np.asarray(X)[:, :, None], dtype=torch.float32)
    y = torch.tensor(np.asarray(y)[:, None], dtype=torch.float32)
    class Net(nn.Module):
        def __init__(self):
            super().__init__(); self.lstm = nn.LSTM(1, hidden_size, batch_first=True); self.fc = nn.Linear(hidden_size, 1)
        def forward(self, x):
            out, _ = self.lstm(x); return self.fc(out[:, -1, :])
    net = Net(); opt = torch.optim.Adam(net.parameters(), lr=0.01); loss_fn = nn.MSELoss()
    net.train()
    for _ in range(int(epochs)):
        opt.zero_grad(); loss = loss_fn(net(X), y); loss.backward(); opt.step()
    def recursive(last, steps):
        hist = list(np.asarray(last, dtype=np.float32)); preds=[]; net.eval()
        with torch.no_grad():
            for _ in range(steps):
                inp = torch.tensor(np.asarray(hist[-lookback:])[None, :, None], dtype=torch.float32)
                val = float(net(inp).item()); preds.append(val); hist.append(val)
        return np.asarray(preds) * std + mean
    pred_test = recursive(z, len(test))
    pred_future = recursive(z, int(future_periods))
    return pred_test, pred_future


def _fit_sarima(train, test, order, seasonal_order):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    model = SARIMAX(train, order=order, seasonal_order=seasonal_order,
                    enforce_stationarity=False, enforce_invertibility=False,
                    simple_differencing=False)
    fitted = model.fit(disp=False)
    return np.asarray(fitted.forecast(steps=len(test)), dtype=float), fitted


def _lag_matrix(values, lags):
    values = np.asarray(values, dtype=float)
    X, y = [], []
    for i in range(lags, len(values)):
        X.append(values[i-lags:i][::-1])
        y.append(values[i])
    return np.asarray(X), np.asarray(y)


def _fit_svr(train, test, future_periods, lags=6, C=10.0, epsilon=0.1, gamma="scale"):
    values = np.asarray(train, dtype=float)
    if len(values) <= lags + 5:
        raise ValueError(f"SVR requires more than {lags + 5} training observations; got {len(values)}.")
    X, y = _lag_matrix(values, lags)
    model = make_pipeline(StandardScaler(), SVR(C=float(C), epsilon=float(epsilon), gamma=gamma))
    model.fit(X, y)
    history = list(values)
    steps = len(test) + int(future_periods)
    preds = []
    for _ in range(steps):
        x = np.asarray(history[-lags:][::-1], dtype=float).reshape(1, -1)
        val = float(model.predict(x)[0])
        preds.append(val); history.append(val)
    return np.asarray(preds[:len(test)]), np.asarray(preds[len(test):]), model


def _naive_forecast(train, steps):
    if len(train) == 0: raise ValueError("Naive forecasting requires training observations.")
    return np.repeat(float(train.iloc[-1]), int(steps))


def _seasonal_naive_forecast(train, steps, season_length):
    season_length = int(season_length)
    if season_length < 2: raise ValueError("Seasonal-naive season length must be at least 2.")
    if len(train) < season_length:
        raise ValueError(f"Seasonal-naive requires at least {season_length} training observations; got {len(train)}.")
    pattern = list(np.asarray(train.iloc[-season_length:], dtype=float))
    return np.asarray([pattern[i % season_length] for i in range(int(steps))], dtype=float)


def compare_forecasters(series: pd.Series, models=None, test_fraction=0.2, arima_order=(1,1,1),
                        seasonal_order=(1,0,1,4), future_periods=4, frequency="W",
                        lstm_lookback=6, lstm_epochs=80, svr_lags=6,
                        seasonal_period=4):
    """Chronological holdout evaluation and optional future forecasts.

    Fits each model using only the training segment for holdout scoring, then
    refits on the full observed series for future forecasts. No random shuffle.
    """
    models = models or ["Naive", "Seasonal Naive", "ARIMA", "SARIMA", "Prophet", "SVR", "LSTM"]
    s = pd.Series(series).dropna().astype(float).sort_index()
    if len(s) < 12:
        raise ValueError("At least 12 regularly spaced observations are required.")
    n_test = max(2, int(np.ceil(len(s) * float(test_fraction))))
    if len(s) - n_test < 8:
        raise ValueError("The chronological split leaves fewer than eight training observations. Use more time points or a smaller holdout fraction.")
    train, test = s.iloc[:-n_test], s.iloc[-n_test:]
    train_fit = train.interpolate(method="time", limit_direction="forward").ffill().bfill()
    full_fit = s.interpolate(method="time", limit_direction="forward").ffill().bfill()
    rows=[]; predictions={}; future_frames={}
    future_idx = pd.date_range(s.index[-1], periods=int(future_periods)+1, freq=frequency)[1:]
    for name in models:
        try:
            if name == "Naive":
                pred = _naive_forecast(train_fit, len(test))
                future = pd.Series(_naive_forecast(full_fit, future_periods), index=future_idx)
            elif name == "Seasonal Naive":
                pred = _seasonal_naive_forecast(train_fit, len(test), seasonal_period)
                future = pd.Series(_seasonal_naive_forecast(full_fit, future_periods, seasonal_period), index=future_idx)
            elif name == "ARIMA":
                pred, _ = _fit_arima(train_fit, test, tuple(arima_order))
                fitted = _fit_arima(full_fit, pd.Series([np.nan], index=[future_idx[0]]), tuple(arima_order))[1]
                future = pd.Series(np.asarray(fitted.forecast(steps=future_periods)), index=future_idx)
            elif name == "SARIMA":
                pred, _ = _fit_sarima(train_fit, test, tuple(arima_order), tuple(seasonal_order))
                fitted = _fit_sarima(full_fit, pd.Series([np.nan], index=[future_idx[0]]), tuple(arima_order), tuple(seasonal_order))[1]
                future = pd.Series(np.asarray(fitted.forecast(steps=future_periods)), index=future_idx)
            elif name == "Prophet":
                pred, _ = _fit_prophet(train_fit, test, future_periods, frequency)
                _, future_df = _fit_prophet(full_fit, pd.Series(dtype=float), future_periods, frequency)
                future = pd.Series(future_df["yhat"].to_numpy(), index=pd.to_datetime(future_df["ds"]))
            elif name == "SVR":
                pred, fut, _ = _fit_svr(train_fit, test, future_periods, lags=svr_lags)
                _, fut_full, _ = _fit_svr(full_fit, pd.Series(dtype=float), future_periods, lags=svr_lags)
                future = pd.Series(fut_full, index=future_idx)
            elif name == "LSTM":
                pred, _ = _fit_lstm(train_fit, test, future_periods, lookback=lstm_lookback, epochs=lstm_epochs)
                _, fut = _fit_lstm(full_fit, pd.Series(dtype=float), future_periods, lookback=lstm_lookback, epochs=lstm_epochs)
                future = pd.Series(fut, index=future_idx)
            else:
                raise ValueError(f"Unsupported forecasting model: {name}")
            predictions[name] = pd.Series(pred, index=test.index)
            future_frames[name] = future
            rows.append({"model":name, **_metrics(test.to_numpy(), pred), "status":"completed", "error":""})
        except Exception as exc:
            rows.append({"model":name, "n_test":0, "mae":np.nan, "rmse":np.nan, "r2":np.nan,
                         "status":"unavailable/failed", "error":f"{type(exc).__name__}: {str(exc)[:220]}"})
    return {"metrics":pd.DataFrame(rows).sort_values("rmse", na_position="last"),
            "actual":test, "predictions":predictions, "future":future_frames,
            "train":train, "series":s}
