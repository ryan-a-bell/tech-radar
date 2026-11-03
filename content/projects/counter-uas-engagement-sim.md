---
id: counter-uas-engagement-sim
name: Counter-UAS Engagement Simulator
status: Idea
topics: [Agents, ML, Data Feeds]
stack: [STK, mesa, PettingZoo, ANSYS HFSS / AEDT, Docker]
repo:
---

A Monte Carlo study tool for sizing a layered small-drone defense around a
fixed site. Planners place radars, electro-optical/infrared cameras, and RF
detectors on terrain, set an incoming threat mix — single drones, coordinated
swarms, low-and-slow quadcopters hugging the tree line — and run thousands of
raids. The output is how often each threat is detected, tracked, and handed off
inside the time available. It is a sizing and placement tool, not a fire-control
system.

The value is in the coupled models. Sensor line-of-sight and coverage come from
an orbital and terrain analysis tool, radar cross-sections and antenna patterns
from electromagnetic simulation, and the attacking swarm is an agent-based model
whose behaviors — saturate, decoy, split up — are trained in a multi-agent
reinforcement-learning environment. Sweeps run in containers across a cluster.
It reuses the mission-rehearsal simulator's machinery with the roles reversed:
instead of flying the drones, you are trying to see them.
