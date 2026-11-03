---
id: practice-room-coach
name: Practice-Room Coach
status: Archived
topics: [Music, STT, ML]
stack: [Sightread, audio.cpp, whisper.cpp]
repo: https://github.com/you/practice-coach
---

A practice companion for piano that listens while you play, follows along in
the score, and afterwards shows where tempo drifted, which passages had wrong
or missed notes, and how a piece improved across a week of sessions. Spoken
commands — "loop bars twelve to sixteen", "slow it to eighty percent" — keep
your hands on the keys.

On-device audio inference handles pitch and onset detection, a small
speech-recognition model listens for the voice commands, and a sight-reading
app supplies the scores and drills. Archived after the prototype: score
following on polyphonic audio needed more than a hobby budget, though the
onset-detection code was reused in the field-notes transcriber.
