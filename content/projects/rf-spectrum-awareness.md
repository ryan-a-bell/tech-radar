---
id: rf-spectrum-awareness
name: RF Spectrum Situational Awareness
status: Idea
topics: [ML, Data Feeds, Agents]
stack: [FISSURE, iroh, Ollama, OpenObserve, grafana]
repo:
---

A distributed spectrum-monitoring network built from small passive
software-defined-radio sensors. Each node sweeps its band, classifies the
emitters it hears, and flags interference or jamming. The nodes share what
they see over a peer-to-peer mesh, building one picture of a contested
spectrum that the comms planner can use to switch frequency or route before a
link actually drops.

The hard part is classification at the edge with intermittent backhaul. An RF
framework handles signal detection, demodulation, and fingerprinting on each
node. The mesh layer syncs detections opportunistically when neighbors are in
range, and a local model turns raw detections into plain-language reports for
the operator ("wideband noise on the UHF relay band, onset 14:02, bearing
north-east"). Detection rates, false alarms, and sensor health stream into
observability dashboards, and the classifier is watched for drift as the RF
environment changes. It is the sensing half of the contested-comms SAR mesh:
that project survives a jammed link, this one sees the jamming coming.
