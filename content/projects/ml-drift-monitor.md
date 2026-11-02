---
id: ml-drift-monitor
name: Model Drift Monitor
status: Active
topics: [ML, Data Feeds]
stack: [evidently, dvc, grafana, OpenObserve]
repo: https://github.com/you/drift-monitor
---

A monitoring service that watches deployed models for data drift and quietly
degrading accuracy. It compares each day's feature distributions against the
training reference, tracks prediction drift and delayed ground-truth accuracy,
and opens an alert — with the offending features ranked — before a stale model
does real damage.

Reference datasets and model versions are pinned with data version control so
every alert points at the exact snapshot the model was trained on, statistical
drift reports are generated per feature, and the metrics and logs stream into
dashboards next to the rest of the infrastructure. The forecaster and the
sensor-anomaly detector are its first two customers; both suffer the same
distribution shift over time.
