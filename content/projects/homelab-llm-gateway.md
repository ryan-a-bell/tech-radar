---
id: homelab-llm-gateway
name: Homelab LLM Gateway
status: Active
topics: [AI, RAG, Agents]
stack: [vLLM, llama.cpp, LibreChat, keycloak, Docker, Kubernetes, OpenObserve]
repo: https://github.com/you/llm-gateway
---

A single, authenticated front door to every model running at home. It serves
large models on the GPU box and small quantized ones on CPU nodes, exposes them
behind one OpenAI-compatible endpoint with per-user keys and quotas, and gives
the household a shared chat interface with conversation history and document
upload.

The interesting work is operational: routing each request to the cheapest
model that can handle it, batching to keep the GPU saturated, single sign-on
in front of everything, and tracing every call so latency, token spend, and
errors are visible. Containers on a small cluster keep it reproducible. The
other local-first projects — the transcriber, the copilot, the trading desk's
agents — all point at this gateway instead of each running their own model.
