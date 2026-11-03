---
id: mbse-model-copilot
name: MBSE Model Copilot
status: Idea
topics: [Agents, RAG, AI]
stack: [SysML v2, Cameo/MagicDraw, syson, docling, Ollama]
repo:
---

An assistant that sits beside a systems model and keeps it honest. It reads
requirement documents and interface control documents, proposes SysML v2
requirement definitions and satisfy links, flags requirements nothing
satisfies, and answers questions like "which parts are affected if the uplink
budget drops by 3 dB?" by walking the model rather than guessing.

Two halves make it work: a document parser turns specifications into
structured text with tables intact, and a model-aware agent queries and edits
the textual SysML through an open-source modeling server while staying
round-trip compatible with the commercial tool the team already uses. A local
model keeps controlled technical data on-premises. The SAR fleet model is the
first test case — its requirements-trace gaps are exactly what the copilot
should close.
