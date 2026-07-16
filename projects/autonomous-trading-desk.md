---
id: autonomous-trading-desk
name: Autonomous Trading Desk
status: Idea
topics: [Trading, Quant, Agents, Data Feeds]
stack: [manual:tradingagents, gs-quant, Riskfolio-Lib, Polygon.io, manual:ibkr-tws, Ollama, Grafana]
repo:
---

A multi-agent trading desk — a hedge fund in a box. Research agents surface
theses from the news and price action, a quant agent prices and backtests them,
a risk agent vetoes anything that breaches position or drawdown limits, and an
execution agent works the resulting orders — all supervised by a human and every
decision logged for the post-mortem.

Structurally this is the same problem as coordinating a rescue fleet: many
autonomous actors sharing one picture, disagreeing, and being reconciled under
hard constraints — here the constraint is risk and capital instead of fuel and
comms. Market data feeds the picture through Polygon, gs-quant handles the
pricing and risk analytics, a dedicated library builds the portfolio, and orders
reach the market through the broker gateway. A local model runs the agent loop so
no thesis or position leaves the desk.
