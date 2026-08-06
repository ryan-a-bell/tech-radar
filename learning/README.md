# Learning Library

The books, articles, videos, and certifications tracked alongside the tech
radar, each one a Markdown file. Like `people/` and `projects/`, this directory
is the **source of truth** — hand-written prose, not scraped JSON.

`build_learning.py` reads every `*.md` here (except this README) and writes
`data/learning.json`, which the **LEARNING** tab (`web/learning.html`) renders.
The `learning.py` CLI writes these files for you and refreshes the JSON in the
same step, so you rarely edit them by hand — but you can.

## File format

Each item is one Markdown file named `<id>.md`: a YAML-style front-matter block
between `---` fences (the structured fields), followed by a free-text body that
is the **blurb**.

```markdown
---
id: ddia                          # unique slug (defaults to the filename)
type: book                        # book | article | video | certification
title: Designing Data-Intensive Applications
author: Martin Kleppmann
year: 2017
status: Read                      # Read | Reading | Queued | Discovered | Shelved
topics: [Data Feeds, Skills]      # from the shared TOPICS vocabulary
pages: 616                        # book length
pages_read:                       # blank = not tracked (parses to null)
rating: 5                         # 1–5, set once Read
added:                            # status date stamps (added/queued/started/
started:                          #   finished/shelved) — set as the item moves
queued:
finished: 2026-03-02
shelved:
---

The reference for how reliable, scalable systems actually store and move
data — replication, partitioning, and the tradeoffs behind every database
pitch deck. This body is the blurb.
```

A blank `key:` parses to `null`; every field is written out even when empty so
you can see what's fillable. Values with a leading `[`, wrapping quotes, or edge
whitespace are quoted — everything else (internal colons, commas, em-dashes) is
written bare.

### Fields

| Field | Notes |
|-------|-------|
| `id` | Unique slug. Defaults to the filename without `.md`. |
| `type` | `book`, `article`, `video`, or `certification`. Decides the length field below. |
| `title` / `author` | Display fields. For a certification, `author` is the issuing org. |
| `year` | Publication/release year (integer). |
| `status` | `Read`, `Reading`, `Queued`, `Discovered`, or `Shelved`. |
| `topics` | Inline list from the shared `TOPICS` vocabulary (`learning_core.py`). |
| length | `pages` + `pages_read` (book), `minutes` (article), `duration` (video), `price` (certification). |
| `rating` | 1–5, set once the item is Read. |
| dates | `added`, `queued`, `started`, `finished`, `shelved` — stamped as the item moves through the pipeline. |
| `shelved_note` | Optional one-liner on why something was set aside; cleared when it leaves Shelved. |
| `source` / `url` | Publication/channel (or exam code) + link, for articles/videos/certifications. Books carry neither. |
| _body_ | The blurb — one honest sentence or two about what the item is. |

## Workflow

```bash
# preferred: let the CLI write the .md and refresh the JSON in one step
python learning.py add "Streaming Systems" --type book --topics "Data Feeds" \
  --blurb "Windowing, watermarks, and exactly-once semantics."
python learning.py status ddia Reading
python learning.py rate ddia 5

# or hand-edit a learning/<id>.md, then republish:
python build_learning.py

# build the static site and preview
python build_site.py
cd site && python -m http.server 8000   # open learning.html
```
