---
id: options-flow-scanner
name: Unusual Options-Flow Scanner
status: Active
topics: [Trading, Quant, Data Feeds]
stack: [ThetaData, vollib, Polygon.io, OpenBB, Grafana]
repo: https://github.com/you/options-flow-scanner
---

A scanner that watches the live options tape for unusual activity — block
prints well above open interest, sweeps hitting the ask across several
exchanges, and sudden jumps in implied volatility on a single strike — and
ranks each alert by how far it sits outside that contract's normal behavior.

Every trade is enriched with greeks and implied volatility computed on the fly,
so an alert carries delta-adjusted notional rather than raw premium. Historical
quotes and trades come from a tick-level options feed, underlying prices from a
second market-data source, and a research terminal is used to sanity-check a
flagged name before it ever reaches the desk. Alert rates, latency, and feed
gaps are charted on a live dashboard. It is the natural input for the
vol-surface lab and the research agents on the trading desk.
