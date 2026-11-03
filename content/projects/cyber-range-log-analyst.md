---
id: cyber-range-log-analyst
name: Cyber Range Log Analyst
status: Idea
topics: [AI, Agents, Data Feeds]
stack: [OpenObserve, keycloak, Ollama]
repo:
---

An analyst's assistant for defensive cyber exercises on a training range.
During the exercise it ingests network flows, host logs, and IDS alerts from
the range and groups related alerts into incidents — this phishing click, that
lateral movement, the later data staging. It writes a running timeline of each
incident so the blue team can see the attack as a story rather than a thousand
alerts, and the white cell can score their detection and response times.

Logs, metrics, and traces land in a single observability store, so the
assistant queries one place rather than a dozen consoles. Single sign-on gives
the blue team, white cell, and observers separate views of the same data. A
local model clusters alerts, summarizes each incident with links to the
underlying log lines, and drafts the after-action report — keeping exercise
data, which often mirrors real network layouts, off any external service. It
uses the same observability stack as the RF spectrum network and points at the
homelab LLM gateway for its model.
