---
id: sar-contested-comms-mesh
name: Contested-Comms SAR Mesh
status: Idea
topics: [Agents, ML, Data Feeds]
stack: [ANSYS HFSS / AEDT, CST Studio Suite, manual:stk, iroh, PettingZoo, UAF, OpenObserve]
repo:
---

The same rescue fleet, but assuming the radios drop. This project layers a
resilient communications mesh over the SAR fleet so vessels and drones keep
sharing a common operating picture when the link to shore is jammed, over the
horizon, or saturated. Craft relay for each other, buffer telemetry through
outages, and fall back to intermittent satellite passes — and the task allocator
has to keep planning while it only sometimes knows where everyone is.

This one is genuinely multi-disciplinary. Antenna patterns and link budgets are
modeled in HFSS and CST, satellite relay windows and line-of-sight come from STK,
the peer-to-peer sync layer is built on iroh, and a UAF architecture ties the
operational, system, and resource views together so the comms design traces back
to the mission. The open research question is decentralized task allocation under
partial observability: agents that commit to a search plan, degrade gracefully as
neighbors go dark, and reconcile the picture when the mesh heals.
