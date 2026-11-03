---
id: tactical-radio-to-report
name: Tactical Radio-to-Report
status: Idea
topics: [STT, AI, Agents]
stack: [whisper.cpp, faster-whisper, Ollama]
repo:
---

Turns push-to-talk radio traffic into structured reports, entirely on a
rugged laptop or handheld with no connection to anything. It listens to a net,
transcribes each transmission through static, clipping, and callsign jargon, and
fills the right template — a 9-line medevac request, a situation report, a
spot report — highlighting any required line that is missing so the operator
can ask for it before the sender goes off the air.

The hard parts are the audio and the format. Radio audio is narrowband, noisy,
and full of procedure words and phonetic-alphabet grid references, so a small
speech-to-text model is tuned on that vocabulary and a faster batch pass
re-transcribes recordings afterwards for the log. A local model maps the
transcript onto the report fields and normalizes grids, times, and callsigns.
It is the field-notes transcriber hardened for a radio net, and the same
"messy radio traffic into structured tasking" step the SAR fleet coordinator
needs from its incident net.
