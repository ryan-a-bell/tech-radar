---
id: microgrid-dispatch-optimizer
name: Microgrid Dispatch & Resilience Optimizer
status: Idea
topics: [ML, Agents, Data Feeds]
stack: [manual:modelica, manual:modelcenter, mesa, vLLM, Grafana]
repo:
---

A dispatch optimizer for a campus microgrid — solar, battery storage, a diesel
backup, and a mix of controllable loads. It forecasts demand and generation for
the day ahead, then schedules storage and generation to ride through grid
outages at least cost, re-planning as the weather and the load actually unfold.

The complexity is closing the loop between a continuous physical model and a
discrete scheduling problem. The plant is modeled in Modelica so the physics of
batteries and inverters are honest, a ModelCenter study sweeps the sizing and
dispatch trade space, and an agent-based model of prosumers reacting to price
signals stresses the schedule against selfish behavior. A forecasting model
drives the day-ahead plan, and operators watch state of charge and reserve margin
on a live dashboard.
