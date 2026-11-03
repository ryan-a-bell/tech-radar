---
id: satellite-collection-planner
name: Satellite Collection Planner
status: Idea
topics: [Agents, ML, Data Feeds]
stack: [STK, PettingZoo, grafana]
repo:
---

A scheduler for a small Earth-observation constellation. Analysts submit
collection requests — image this port daily, revisit this region within six
hours of a cue, record emitters in this area — and the planner assigns each
request to a satellite pass. It balances priority, cloud forecasts, sensor
slew limits, onboard storage, and ground-station downlink windows, and re-plans
the whole schedule when an urgent request arrives.

Access windows, sensor footprints, and downlink contacts come from orbital
analysis, so the planner only ever reasons about geometry that is physically
possible. Allocation is treated as a multi-agent problem: each satellite bids
on requests it can serve, and a policy trained in a multi-agent
reinforcement-learning environment learns when to hold capacity back for
cue-driven requests rather than filling every pass. Request backlog, fulfilment
rate, and age-of-information per target sit on a live dashboard. It is the
orbital cousin of the SAR fleet coordinator's re-tasking problem, and the
satellite relay windows it computes are the same ones the contested-comms mesh
falls back on.
