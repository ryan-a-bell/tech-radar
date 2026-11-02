---
id: generative-fixture-designer
name: Generative Fixture Designer
status: Idea
topics: [CNC, 3D Printing, AI]
stack: [Autodesk Fusion, FreeCAD, PrusaSlicer, Ollama]
repo:
---

An idea for designing workholding fixtures automatically. Give it a part model
and the machining operations planned for it, and it proposes soft jaws, vise
fixtures, or a printed nest that locates the part repeatably, clears every tool
path, and resists the cutting forces — then exports a printable or machinable
fixture body.

The interesting problem is reasoning about geometry under constraints: picking
datum faces, checking tool-path clearance, and trading print time against
stiffness. Parametric CAD scripts generate candidate fixtures, a slicer
estimates print time and material for the printed variants, and a local model
reads the setup sheet to infer which faces matter. It borrows the trade-space
sweep idea from the microgrid sizing study, aimed at a vise instead of a
battery bank.
