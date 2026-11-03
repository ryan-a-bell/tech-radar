---
id: field-notes-transcriber
name: Field-Notes Transcriber
status: Shipped
topics: [STT, RAG, AI]
stack: [faster-whisper, WhisperX, Ollama, Open WebUI]
repo: https://github.com/you/field-notes
---

Turns voice memos, meeting recordings, and site-walk dictation into searchable,
speaker-labelled notes. Drop an audio file in a folder and it is transcribed,
diarized, timestamped, summarized into action items, and indexed so you can ask
"what did we decide about the antenna mount?" and land on the exact second of
the recording.

Everything runs locally: a fast speech-to-text engine does the first pass, a
word-level alignment and diarization step attributes each sentence to a
speaker, and a local model writes the summary and answers questions over the
transcript archive through a chat front-end. Shipped and in daily use — it is
the audio sibling of the document intelligence engine, grounding answers in a
recording instead of a scanned page.
