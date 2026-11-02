---
id: uas-mission-rehearsal-sim
name: UAS Mission Rehearsal Simulator
status: Active
topics: [Agents, ML, Data Feeds]
stack: [STK, mesa, PettingZoo, Docker, Grafana]
repo: https://github.com/you/mission-rehearsal
---

A simulator for rehearsing multi-drone missions before they fly. Planners load
terrain, airspace restrictions, weather, and a fleet roster, then run hundreds
of Monte Carlo rehearsals in which vehicles lose links, batteries sag in the
cold, and targets move — producing a mission-success distribution instead of a
single optimistic plan.

Sensor footprints and line-of-sight geometry come from an orbital and terrain
analysis tool, an agent-based model plays the environment and the other
airspace users, and a multi-agent reinforcement-learning environment lets the
same allocation policy used by the SAR fleet coordinator be trained and stress
tested here first. Runs are containerized so a sweep fans out across a
cluster, and the outcome distributions land on a dashboard.
