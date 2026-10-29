---
id: sensor-anomalies
name: Sensor Telemetry Anomalies
status: Idea
topics: [ML, Data Feeds]
repo:
---

An idea for detecting anomalies in industrial sensor streams over time. The
plan: ingest telemetry from many sensors, resample the irregular timestamps
onto a regular grid, decompose trend and seasonality, and fit a rolling forecast
so points that break the predicted band get flagged.

Structurally this is the same shape as forecasting a financial series — lagged
features, rolling windows, drift as the distribution shifts over time, and a
signal that fires when the observed value leaves the forecast window. Different
domain, same temporal machinery, so the tooling should overlap heavily.
