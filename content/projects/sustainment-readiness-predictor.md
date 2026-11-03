---
id: sustainment-readiness-predictor
name: Sustainment & Readiness Predictor
status: Active
topics: [ML, OCR, RAG, Data Feeds]
stack: [docling, PaddleOCR, evidently, dvc, Ollama]
repo: https://github.com/you/readiness-predictor
---

Predictive maintenance for a vehicle fleet. It combines maintenance-action
records, onboard sensor telemetry, and parts-supply data to forecast which
components on which vehicles are likely to fail in the next 30, 60, and 90 days.
It then recommends which spares to order and which inspections to pull forward
so that mission readiness does not drop.

Half the problem is the data. Decades of maintenance history live in scanned
work orders and technical manuals, so OCR and document parsing lift fault codes,
parts, and procedures off the page into structured records. A survival-style
failure model trains on the cleaned history, with every training snapshot
version-controlled so a prediction can be traced back to the data behind it.
Drift reports catch a model going stale when a new vehicle variant or operating
theater changes the failure patterns. A local model explains each
recommendation and cites the manual paragraph and maintenance records behind
it. It reuses the sensor-anomaly detector's temporal machinery and the document
engine's OCR pipeline.
