---
id: factor-research-lab
name: Equity Factor Research Lab
status: Paused
topics: [Quant, Trading, ML]
stack: [Qlib, AlphaLens, PyFolio, Empyrical, Statsmodels]
repo: https://github.com/you/factor-lab
---

A research harness for cross-sectional equity factors — value, momentum,
quality, low volatility, and a handful of ML-learned alphas — that measures
each factor's information coefficient, turnover, and decay across holding
periods before anything is allowed near a portfolio.

The discipline is in the evaluation: point-in-time data so nothing leaks from
the future, factor returns neutralized against sector and size, regression
diagnostics on every exposure, and a tear sheet that shows drawdowns and
rolling Sharpe rather than one flattering number. Paused until the data
pipeline can serve survivorship-free fundamentals; the surviving factors are
meant to feed the portfolio optimizer as expected-return views.
