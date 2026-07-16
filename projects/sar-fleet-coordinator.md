---
id: sar-fleet-coordinator
name: SAR Fleet Coordinator
status: Active
topics: [AI, ML, Agents, Data Feeds]
stack: [manual:stk, SysML v2, PettingZoo, Ollama, Grafana, Docker]
repo: https://github.com/you/sar-fleet-coordinator
---

Coordination software for search-and-rescue missions flown by a mixed fleet of
unmanned surface vessels and UAVs. An incident commander drops a last-known
position and a drift model; the planner divides the search area into cells,
assigns each craft a sweep pattern sized to its sensor footprint and endurance,
and re-tasks the fleet live as the probability-of-detection map updates from
every pass.

The hard part is the joint plan: many craft, overlapping sensor coverage, comms
and fuel limits, and a survivor whose position drifts with wind and current. A
multi-agent policy handles the task allocation, STK supplies the sensor- and
comms-coverage geometry, and the whole system-of-systems — vehicle, payload, and
ground-station interfaces — is specified in SysML so the pieces stay consistent
as the fleet grows. An on-board local model turns messy radio traffic into
structured tasking, and the ground station watches fleet health on a live
dashboard.
