---
id: gsd-core-app
name: GSD Core App
status: Active
topics: [Quant, Agents]
stack: [manual:gsd-core, Cursor, Ollama]
repo: https://github.com/open-gsd/gsd-core
---

A local-first "get stuff done" runner that turns a plain-language goal into a
sequence of executed steps. It plans a task graph, routes each step to a local
model, and keeps the whole loop on the machine so nothing leaves the laptop.

The core is a small library that other tools build on: a scheduler, a tool
registry, and a persistence layer for run history. Day-to-day development leans
on an AI editor for the glue code and a local model server for the planning and
reflection calls, so the whole thing runs without an API key.
