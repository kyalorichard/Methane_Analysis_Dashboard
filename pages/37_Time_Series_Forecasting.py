import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import importlib.util
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
from analysis_engine.time_series_forecasting import prepare_series, compare_forecasters
from analysis_engine.settings_config import load_active_settings

render_sidebar_navigation()
_active_settings = load_active_settings(st.session_state)
_forecast_cfg = _active_settings.get("forecasting", {})
header("Time-series forecasting", "Compare naïve benchmarks, ARIMA/SARIMA, Prophet, SVR and LSTM using chronological holdout validation.")
df = get_data()
roles = get_roles(df)
nums = numeric_cols(df)
if df is None or df.empty:
    st.info("Import a dataset to begin.")
    st.stop()

st.warning("Forecasting requires repeated observations over time. A dataset with one measurement per animal and no temporal repetition cannot support within-series forecasting. Forecasts are statistical projections, not validated methane-flux estimates.")
date_candidates = [c for c in df.columns if any(k in c.lower() for k in ["date", "time", "timestamp", "visit"]) ]
def_date = roles.get("date") if roles.get("date") in df.columns else (date_candidates[0] if date_candidates else None)
date_col = choose_col(df, "Date/time variable", def_date, date_candidates or list(df.columns))
target_candidates = [c for c in nums if c != roles.get("animal_id")]
target = choose_col(df, "Methane outcome to forecast", roles.get("methane"), target_candidates)
animal = roles.get("animal_id") if roles.get("animal_id") in df.columns else None
if animal:
    animal_opts = ["All animals (aggregate)"] + sorted(df[animal].dropna().astype(str).unique().tolist())
    scope = st.selectbox("Forecasting series", ["Population aggregate", "Individual animal"])
    animal_value = st.selectbox("Animal", animal_opts, disabled=(scope == "Population aggregate"))
    if scope == "Population aggregate": animal_value = "All animals (aggregate)"
else:
    animal_value = None
    st.caption("No Animal ID mapping found. The page will treat the selected dataset as one time series.")

c1,c2,c3 = st.columns(3)
with c1: frequency_label = st.selectbox("Time frequency", ["Daily", "Weekly", "Monthly"], index={"D":0,"W":1,"ME":2}.get(_forecast_cfg.get("frequency", "W"),1))
with c2: aggregation = st.selectbox("Within-period aggregation", ["mean", "median"], index=["mean","median"].index(_forecast_cfg.get("aggregation", "mean")))
with c3: test_fraction = st.slider("Chronological holdout (%)", 10, 40, int(float(_forecast_cfg.get("test_fraction", 0.2))*100), 5) / 100
freq = {"Daily":"D", "Weekly":"W", "Monthly":"ME"}[frequency_label]
available_models = ["Naive", "Seasonal Naive", "ARIMA", "SARIMA", "SVR"]
if importlib.util.find_spec("prophet") is not None: available_models.append("Prophet")
if importlib.util.find_spec("torch") is not None: available_models.append("LSTM")
model_order = ["Naive", "Seasonal Naive", "ARIMA", "SARIMA", "Prophet", "SVR", "LSTM"]
models = st.multiselect("Forecasting models", model_order, default=[m for m in _forecast_cfg.get("models", available_models) if m in available_models])
missing_optional = [name for name, ok in [("Prophet", importlib.util.find_spec("prophet") is not None), ("LSTM / PyTorch", importlib.util.find_spec("torch") is not None)] if not ok]
if missing_optional:
    st.caption("Optional packages not detected in this environment: " + ", ".join(missing_optional) + ". Install from requirements-forecasting-optional.txt to enable them.")
with st.expander("Model configuration"):
    a,b,c = st.columns(3)
    with a: p = st.number_input("ARIMA p",0,8,int(_forecast_cfg.get("arima_order", [1,1,1])[0]))
    with b: d = st.number_input("ARIMA d",0,2,int(_forecast_cfg.get("arima_order", [1,1,1])[1]))
    with c: q = st.number_input("ARIMA q",0,8,int(_forecast_cfg.get("arima_order", [1,1,1])[2]))
    a,b,c = st.columns(3)
    with a: horizon = st.number_input("Future forecast periods",1,365,int(_forecast_cfg.get("horizon",4)))
    with b: lookback = st.number_input("LSTM lookback periods",3,100,int(_forecast_cfg.get("lstm_lookback",6)))
    with c: epochs = st.number_input("LSTM training epochs",20,1000,int(_forecast_cfg.get("lstm_epochs",80)),20)
    a,b,c = st.columns(3)
    with a: seasonal_period = st.number_input("Season length (periods)",2,365,int(_forecast_cfg.get("seasonal_period",4)),help="Set to the number of observations in one seasonal cycle, e.g. 12 for monthly annual seasonality.")
    with b: svr_lags = st.number_input("SVR lag features",2,100,int(_forecast_cfg.get("svr_lags",6)))
    with c: seasonal_p = st.number_input("SARIMA seasonal P",0,5,int(_forecast_cfg.get("sarima_order",[1,0,1,4])[0]))

if st.button("Prepare time series", type="secondary"):
    try:
        series = prepare_series(df, date_col, target, freq, animal if animal else None,
                                animal_value, aggregation)
        st.session_state["forecast_series"] = series
        st.session_state["forecast_meta"] = {"target":target,"date":date_col,"frequency":freq,"scope":animal_value}
    except Exception as exc:
        st.error(str(exc))

series = st.session_state.get("forecast_series")
if series is not None:
    st.subheader("Prepared time series")
    valid_n = int(series.notna().sum())
    missing_n = int(series.isna().sum())
    metric_row([("TIME POINTS",f"{len(series):,}","Regularised index"),("OBSERVED PERIODS",f"{valid_n:,}","Non-missing"),("GAPS",f"{missing_n:,}","Periods requiring review")])
    st.plotly_chart(__import__('plotly.express').express.line(series.rename(target).reset_index(), x="index", y=target, title=f"{target} — prepared {frequency_label.lower()} series"), use_container_width=True)
    st.caption("Missing time bins are not silently treated as observed values. Review gaps and measurement coverage before interpreting forecasts.")
    if st.button("Run forecasting comparison", type="primary", disabled=not models):
        try:
            with st.spinner("Fitting forecasting models and evaluating the chronological holdout..."):
                result = compare_forecasters(series, models=models, test_fraction=test_fraction,
                    arima_order=(int(p),int(d),int(q)), future_periods=int(horizon), frequency=freq,
                    lstm_lookback=int(lookback), lstm_epochs=int(epochs),
                    seasonal_order=(int(seasonal_p),0,1,int(seasonal_period)),
                    seasonal_period=int(seasonal_period), svr_lags=int(svr_lags))
            st.session_state["forecast_results"] = result
        except Exception as exc:
            st.error(f"Forecasting failed: {exc}")
    result = st.session_state.get("forecast_results")
    if result:
        st.subheader("Out-of-time model comparison")
        st.dataframe(result["metrics"], use_container_width=True, hide_index=True)
        st.download_button("Download forecasting metrics", result["metrics"].to_csv(index=False).encode(), "methane_forecasting_metrics.csv", "text/csv")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=result["train"].index,y=result["train"].values,name="Training",mode="lines"))
        fig.add_trace(go.Scatter(x=result["actual"].index,y=result["actual"].values,name="Holdout actual",mode="lines+markers"))
        for name,pred in result["predictions"].items(): fig.add_trace(go.Scatter(x=pred.index,y=pred.values,name=f"{name} holdout",mode="lines+markers"))
        fig.update_layout(title="Observed versus out-of-time predictions",xaxis_title="Date",yaxis_title=target)
        st.plotly_chart(fig,use_container_width=True)
        if result["future"]:
            st.subheader("Future forecasts (models refitted on all observed data)")
            future_df = pd.concat(result["future"],axis=1)
            st.dataframe(future_df,use_container_width=True)
            st.download_button("Download future forecasts",future_df.to_csv().encode(),"methane_future_forecasts.csv","text/csv")
        st.info("Metrics are calculated on the final chronological holdout. Compare models on the same time range. For stronger evidence, use rolling-origin evaluation and independent temporal or farm-level validation when the dataset supports it.")

st.divider()
st.subheader("Model interpretation and validation")
st.markdown("**Naïve** carries the last training observation forward. **Seasonal Naïve** repeats the last observed seasonal cycle. **ARIMA/SARIMA** model autoregressive and moving-average structure, with SARIMA adding seasonal terms. **Prophet** models trend and seasonality. **SVR** uses lagged values as predictors and recursively forecasts ahead. **LSTM** learns sequence patterns from a rolling lookback window.")
st.info("Use the same chronological holdout for all models. Seasonal models require a defensible season length and enough complete cycles. Recursive SVR/LSTM forecasts can accumulate error over longer horizons. For publication-grade evidence, add rolling-origin backtesting and prediction intervals.")
