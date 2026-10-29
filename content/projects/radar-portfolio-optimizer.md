---
id: radar-portfolio-optimizer
name: Portfolio Optimizer
status: Paused
topics: [Quant, Trading, ML]
stack: [Riskfolio-Lib, gs-quant]
repo: https://github.com/you/portfolio-optimizer
---

A backtesting harness for portfolio construction. It takes a universe of
tickers and a set of constraints, then compares allocation methods — mean
variance, hierarchical risk parity, and a few risk-budgeting schemes — on the
same out-of-sample window so the tradeoffs are visible side by side.

Uses a dedicated optimization library for the allocation math and gs-quant for
the risk and pricing pieces. Paused while I decide whether to add a proper
market-data source instead of the CSVs it reads today.
