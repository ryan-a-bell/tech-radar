---
id: trading-timeseries
name: Trading Time-Series Forecaster
status: Active
topics: [Quant, Trading, ML]
stack: [gs-quant, QuantPy]
repo: https://github.com/you/ts-forecaster
---

Walk-forward forecasting of equity price series. It builds lagged features and
rolling-window statistics from the raw series, trains a model per volatility
regime, and validates strictly out-of-sample so nothing leaks from the future.

The interesting problems are all temporal: resampling to a regular grid,
handling gaps and irregular timestamps, decomposing trend and seasonality, and
measuring drift as the distribution shifts over time. The output is a forecast
band and a signal that fires when the observed value breaks the predicted
window.
