---
id: options-vol-surface
name: Options Vol-Surface Lab
status: Idea
topics: [Quant, Trading, Data Feeds]
repo:
---

An idea, no code yet. I want to build and calibrate an implied-volatility
surface for equity options: pull an options chain, fit a no-arbitrage surface
across strikes and expiries, and price exotic payoffs off it. The interesting
part is the calibration — SVI or SABR fits, arbitrage checks, and a clean way to
interpolate the surface for pricing.

Because there is no declared stack, the recommendations below are the whole
suggested tech stack, inferred purely from this description — option pricing
libraries, a quant analytics toolkit, and a market-data feed for the chains.
